import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.application import Application
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def _enrich(app: Application, db_row) -> ApplicationResponse:
    """Attach job details to application response."""
    resp = ApplicationResponse.model_validate(app)
    if hasattr(db_row, "Job"):
        job = db_row.Job
        resp.job_title = job.title
        resp.company = job.company
        resp.job_url = job.url
    return resp


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def create_application(
    body: ApplicationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Track a job application (mark as saved/applied)."""
    app = Application(
        user_id=user_id,
        job_id=body.job_id,
        resume_version_id=body.resume_version_id,
        cover_letter_id=body.cover_letter_id,
        notes=body.notes,
        platform=body.platform,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.get("/", response_model=list[ApplicationResponse])
async def list_applications(
    status: str | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked applications, optionally filtered by status."""
    from app.models.job import Job
    stmt = (
        select(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .where(Application.user_id == user_id)
        .order_by(Application.updated_at.desc())
    )
    if status:
        stmt = stmt.where(Application.status == status)

    result = await db.execute(stmt)
    rows = result.all()

    responses = []
    for row in rows:
        app = row[0]
        job = row[1]
        resp = ApplicationResponse.model_validate(app)
        resp.job_title = job.title
        resp.company = job.company
        resp.job_url = job.url
        responses.append(resp)
    return responses


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        from fastapi import HTTPException
        raise HTTPException(404, "Application not found")
    return ApplicationResponse.model_validate(app)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update application status (e.g., saved → applied → interviewing)."""
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        from fastapi import HTTPException
        raise HTTPException(404, "Application not found")

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(app, key, value)

    await db.flush()
    await db.refresh(app)
    return ApplicationResponse.model_validate(app)


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    app = result.scalar_one_or_none()
    if app:
        await db.delete(app)
