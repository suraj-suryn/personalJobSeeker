import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.outreach import CoverLetter
from app.schemas.application import (
    CoverLetterGenerateRequest,
    CoverLetterResponse,
    OutreachGenerateRequest,
    OutreachResponse,
)

router = APIRouter(tags=["documents"])


# ─── Cover Letters ──────────────────────────────────────────────────────────

cover_letter_router = APIRouter(prefix="/cover-letters")


@cover_letter_router.post("/generate", response_model=CoverLetterResponse, status_code=201)
async def generate_cover_letter(
    body: CoverLetterGenerateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a personalized cover letter for a job."""
    from app.agents.cover_letter_agent import CoverLetterAgent
    from app.services.auth_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    agent = CoverLetterAgent(db)
    letter = await agent.generate(
        user_id=user_id,
        resume_id=body.resume_id,
        job_id=body.job_id,
        tone=body.tone,
        provider=user.llm_provider,
    )
    return CoverLetterResponse.model_validate(letter)


@cover_letter_router.get("/", response_model=list[CoverLetterResponse])
async def list_cover_letters(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoverLetter)
        .where(CoverLetter.user_id == user_id)
        .order_by(CoverLetter.created_at.desc())
    )
    return [CoverLetterResponse.model_validate(cl) for cl in result.scalars().all()]


@cover_letter_router.get("/{letter_id}/download/{fmt}")
async def download_cover_letter(
    letter_id: uuid.UUID,
    fmt: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoverLetter).where(CoverLetter.id == letter_id, CoverLetter.user_id == user_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        from fastapi import HTTPException
        raise HTTPException(404, "Cover letter not found")

    if fmt == "pdf" and letter.file_path_pdf and Path(letter.file_path_pdf).exists():
        return FileResponse(letter.file_path_pdf, media_type="application/pdf", filename=f"cover_letter_{letter_id}.pdf")
    elif fmt == "docx" and letter.file_path_docx and Path(letter.file_path_docx).exists():
        return FileResponse(
            letter.file_path_docx,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"cover_letter_{letter_id}.docx",
        )
    from fastapi import HTTPException
    raise HTTPException(404, "File not found")


# ─── Outreach Messages ──────────────────────────────────────────────────────

outreach_router = APIRouter(prefix="/outreach")


@outreach_router.post("/generate", response_model=OutreachResponse, status_code=201)
async def generate_outreach(
    body: OutreachGenerateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a LinkedIn message, email draft, or follow-up."""
    from app.agents.cover_letter_agent import OutreachAgent
    from app.services.auth_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    agent = OutreachAgent(db)
    msg = await agent.generate(
        user_id=user_id,
        job_id=body.job_id,
        resume_id=body.resume_id,
        message_type=body.message_type,
        recipient_name=body.recipient_name,
        provider=user.llm_provider,
    )
    return OutreachResponse.model_validate(msg)


@outreach_router.get("/", response_model=list[OutreachResponse])
async def list_outreach(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.outreach import OutreachMessage
    result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.user_id == user_id)
        .order_by(OutreachMessage.created_at.desc())
    )
    return [OutreachResponse.model_validate(m) for m in result.scalars().all()]
