"""
Desktop and browser push notifications.
Uses plyer for Windows/macOS/Linux native toasts.
"""

import logging
import uuid

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_desktop_notification(title: str, message: str, app_icon: str = "") -> None:
    """Send a native desktop toast notification (Windows/macOS/Linux)."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message[:256],  # plyer message length limit
            app_name="PersonalJobSeeker",
            app_icon=app_icon,
            timeout=10,
        )
    except Exception as exc:
        logger.debug("Desktop notification failed (non-critical): %s", exc)


async def send_new_jobs_notification(db, new_jobs: list) -> None:
    """
    Send notifications for newly found jobs.
    Sends desktop notification + email if configured.
    """
    if not new_jobs:
        return

    count = len(new_jobs)

    # Desktop notification (instant)
    if count == 1:
        job = new_jobs[0]
        title = f"New Job: {job.get('title', 'Job Found')}"
        message = f"{job.get('company', '')} • {job.get('location', 'Remote')}"
    else:
        title = f"🔔 {count} New Jobs Found"
        message = "Open JobSeeker to see new matches"

    send_desktop_notification(title=title, message=message)

    # Email notification
    try:
        from app.services.email_service import send_new_jobs_notification as send_email_notification
        job_dicts = [j if isinstance(j, dict) else {
            "title": getattr(j, "title", ""),
            "company": getattr(j, "company", ""),
            "location": getattr(j, "location", ""),
            "url": getattr(j, "url", ""),
            "source": getattr(j, "source", ""),
            "salary_min": getattr(j, "salary_min", None),
            "salary_max": getattr(j, "salary_max", None),
            "salary_currency": getattr(j, "salary_currency", ""),
        } for j in new_jobs]
        await send_email_notification(job_dicts)
    except Exception as exc:
        logger.warning("Email notification failed: %s", exc)
