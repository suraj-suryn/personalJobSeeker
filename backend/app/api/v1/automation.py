"""
Browser Automation API — manages Playwright application sessions.
Includes WebSocket endpoint for real-time automation status.
"""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.browser_agent import (
    AutomationStatus,
    cancel_session,
    confirm_session,
    create_session,
    get_session,
    run_application,
)
from app.core.security import get_current_user_id
from app.database import get_db

router = APIRouter(prefix="/automation", tags=["automation"])


@router.post("/start")
async def start_automation(
    job_id: uuid.UUID,
    resume_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a browser automation session to apply for a job.
    Returns a session_id to track progress via WebSocket or polling.
    
    SAFETY: Form will NOT be submitted without explicit /confirm call.
    """
    from sqlalchemy import select
    from app.models.job import Job
    from app.models.resume import Resume
    from app.services.resume_service import get_resume

    # Load job URL
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(404, "Job not found")

    # Load resume
    resume = await get_resume(db, resume_id, user_id)
    resume_data = resume.parsed_data or {}

    session_id = str(uuid.uuid4())
    create_session(session_id)

    background_tasks.add_task(
        run_application,
        session_id=session_id,
        job_url=job.url,
        resume_data=resume_data,
        resume_file_path=resume.file_path,
    )

    return {
        "session_id": session_id,
        "status": "started",
        "message": "Browser automation started. Connect to /ws/automation/{session_id} for real-time updates.",
    }


@router.get("/status/{session_id}")
async def get_automation_status(
    session_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Poll the status of an automation session."""
    session = get_session(session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found or already completed")

    return {
        "session_id": session_id,
        "status": session["status"],
        "events": session["events"][-10:],  # Last 10 events
        "created_at": session.get("created_at"),
    }


@router.post("/confirm/{session_id}")
async def confirm_submission(
    session_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Confirm and submit the filled application form.
    REQUIRED before the browser agent will click Submit.
    """
    success = confirm_session(session_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(400, "Session not in ready_to_submit state or not found")
    return {"message": "Submission confirmed. Form is being submitted..."}


@router.post("/cancel/{session_id}")
async def cancel_automation(
    session_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Cancel an active automation session."""
    cancel_session(session_id)
    return {"message": "Session cancelled"}


@router.websocket("/ws/automation/{session_id}")
async def ws_automation(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time automation status.
    Frontend connects here to receive live events (captcha_required, ready_to_submit, etc.)
    """
    await websocket.accept()

    session = get_session(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    # Register WebSocket callback
    async def ws_notify(event_type: str, data: dict) -> None:
        try:
            await websocket.send_json({"type": event_type, **data})
        except Exception:
            pass

    session["ws_callback"] = ws_notify

    try:
        # Send current events immediately
        for event in session.get("events", []):
            await websocket.send_json({"type": event["type"], **event["data"]})

        # Keep connection alive until session ends
        while True:
            status = session.get("status")
            if status in (
                AutomationStatus.submitted,
                AutomationStatus.cancelled,
                AutomationStatus.error,
            ):
                break
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                pass  # Heartbeat — session still active
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        session.pop("ws_callback", None)
