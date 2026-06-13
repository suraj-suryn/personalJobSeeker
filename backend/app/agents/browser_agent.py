"""
Browser Automation Agent — Playwright-based job application automation.

Safety rules:
  1. NEVER auto-submits a form. Always requires explicit user confirmation.
  2. Pauses at CAPTCHA / OTP — sends WebSocket event to frontend.
  3. User must call POST /automation/confirm/{session_id} to submit.
  4. User can cancel at any time with POST /automation/cancel/{session_id}.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AutomationStatus(str, Enum):
    pending = "pending"
    navigating = "navigating"
    filling = "filling"
    captcha_required = "captcha_required"
    otp_required = "otp_required"
    ready_to_submit = "ready_to_submit"
    submitted = "submitted"
    cancelled = "cancelled"
    error = "error"


# In-memory session store for active automation sessions
# Key: session_id (str) → {status, events, page, browser, confirm_event, cancel_event}
_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def create_session(session_id: str) -> dict:
    session = {
        "id": session_id,
        "status": AutomationStatus.pending,
        "events": [],
        "page": None,
        "browser": None,
        "confirm_event": asyncio.Event(),
        "cancel_event": asyncio.Event(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }
    _sessions[session_id] = session
    return session


def _emit(session: dict, event_type: str, data: dict | None = None) -> None:
    session["events"].append({
        "type": event_type,
        "data": data or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    session["status"] = event_type
    logger.info("Automation session %s: %s", session["id"], event_type)


async def run_application(
    session_id: str,
    job_url: str,
    resume_data: dict,
    resume_file_path: str | None = None,
    ws_callback=None,  # async callable(event_type, data)
) -> None:
    """
    Full application automation flow.
    Runs as a FastAPI background task.
    """
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    session = get_session(session_id)
    if not session:
        session = create_session(session_id)

    async def notify(event_type: str, data: dict | None = None) -> None:
        _emit(session, event_type, data)
        if ws_callback:
            try:
                await ws_callback(event_type, data or {})
            except Exception:
                pass

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            session["browser"] = browser
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            session["page"] = page

            # Navigate to application page
            await notify("navigating", {"url": job_url})
            await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Detect if this is a direct apply form
            await notify("filling", {"message": "Analyzing form fields..."})
            await _autofill_form(page, resume_data)

            # Upload resume if available
            if resume_file_path:
                await _upload_resume(page, resume_file_path)

            # Detect CAPTCHA
            if await _has_captcha(page):
                await notify("captcha_required", {"message": "CAPTCHA detected. Please solve it in the browser window."})
                # Relaunch visible browser for user interaction
                await browser.close()
                visible_browser = await p.chromium.launch(headless=False)
                vis_context = await visible_browser.new_context()
                vis_page = await vis_context.new_page()
                session["browser"] = visible_browser
                session["page"] = vis_page
                await vis_page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                await _autofill_form(vis_page, resume_data)
                if resume_file_path:
                    await _upload_resume(vis_page, resume_file_path)

            # Signal ready for user review
            await notify("ready_to_submit", {
                "message": "Form filled. Review and confirm to submit.",
                "url": page.url if not session["browser"].is_connected() else job_url,
            })

            # Wait for user confirmation or cancellation (max 10 minutes)
            done, _ = await asyncio.wait(
                [
                    asyncio.create_task(session["confirm_event"].wait()),
                    asyncio.create_task(session["cancel_event"].wait()),
                ],
                timeout=600,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if session["cancel_event"].is_set():
                await notify("cancelled", {"message": "Application cancelled by user"})
                return

            if not done:
                await notify("error", {"message": "Session timed out (10 min)"})
                return

            # User confirmed — submit the form
            active_page = session.get("page")
            if active_page:
                submit_btn = await active_page.query_selector(
                    'button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Apply")'
                )
                if submit_btn:
                    await submit_btn.click()
                    await asyncio.sleep(2)
                    await notify("submitted", {"message": "Application submitted successfully!", "url": active_page.url})
                else:
                    await notify("error", {"message": "Could not find submit button. Please submit manually."})

    except Exception as exc:
        logger.exception("Browser automation error: %s", exc)
        _emit(session, "error", {"message": str(exc)})
    finally:
        browser = session.get("browser")
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        _sessions.pop(session_id, None)


async def _autofill_form(page, resume_data: dict) -> None:
    """Attempt to fill common form fields from resume data."""
    field_map = {
        # Name variations
        r'[name*="first" i], [id*="first" i], [placeholder*="First name" i]': resume_data.get("name", "").split()[0] if resume_data.get("name") else "",
        r'[name*="last" i], [id*="last" i], [placeholder*="Last name" i]': " ".join(resume_data.get("name", "").split()[1:]) if resume_data.get("name") else "",
        r'[name*="fullname" i], [name*="full_name" i], [placeholder*="Full name" i]': resume_data.get("name", ""),
        # Contact
        r'[name*="email" i], [id*="email" i], [type="email"]': resume_data.get("email", ""),
        r'[name*="phone" i], [id*="phone" i], [type="tel"]': resume_data.get("phone", ""),
        # Location
        r'[name*="location" i], [name*="city" i], [placeholder*="City" i]': resume_data.get("location", ""),
        # LinkedIn
        r'[name*="linkedin" i], [placeholder*="LinkedIn" i]': resume_data.get("linkedin_url", ""),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            elements = await page.query_selector_all(selector)
            for el in elements[:1]:  # Fill only first match
                await el.fill(str(value))
                await asyncio.sleep(0.3)
        except Exception:
            pass  # Silently skip unfillable fields


async def _upload_resume(page, file_path: str) -> None:
    """Find file input and upload resume."""
    try:
        file_inputs = await page.query_selector_all('input[type="file"]')
        for inp in file_inputs:
            accept = await inp.get_attribute("accept") or ""
            if "pdf" in accept.lower() or "doc" in accept.lower() or not accept:
                await inp.set_input_files(file_path)
                await asyncio.sleep(1)
                break
    except Exception as exc:
        logger.debug("Resume upload attempt failed: %s", exc)


async def _has_captcha(page) -> bool:
    """Detect common CAPTCHA patterns."""
    try:
        captcha_selectors = [
            ".g-recaptcha",
            "#recaptcha",
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".h-captcha",
            "[data-sitekey]",
        ]
        for sel in captcha_selectors:
            el = await page.query_selector(sel)
            if el:
                return True
    except Exception:
        pass
    return False


def confirm_session(session_id: str) -> bool:
    session = _sessions.get(session_id)
    if session and session["status"] == AutomationStatus.ready_to_submit:
        session["confirm_event"].set()
        return True
    return False


def cancel_session(session_id: str) -> bool:
    session = _sessions.get(session_id)
    if session:
        session["cancel_event"].set()
        return True
    return False
