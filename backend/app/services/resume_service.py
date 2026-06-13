import logging
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.embeddings import generate_embedding
from app.models.resume import Resume
from app.services.vector_service import upsert_resume_embedding

logger = logging.getLogger(__name__)
settings = get_settings()


async def save_and_parse_resume(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
    is_primary: bool = False,
) -> Resume:
    """
    Full pipeline:
    1. Save uploaded file to disk
    2. Create Resume DB record (status=pending)
    3. Trigger background parse + embed
    """
    from app.agents.resume_parser import ResumeParser

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
        )

    # Validate file type
    filename = file.filename or "resume"
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are supported",
        )

    # Save file
    upload_dir = Path(settings.upload_dir) / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / safe_name

    with open(file_path, "wb") as f:
        f.write(contents)

    # Unset previous primary if needed
    if is_primary:
        result = await db.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.is_primary == True)  # noqa: E712
        )
        for r in result.scalars().all():
            r.is_primary = False

    # Create DB record
    resume = Resume(
        user_id=user_id,
        filename=filename,
        file_path=str(file_path),
        file_type=ext.lstrip("."),
        is_primary=is_primary,
        parse_status="processing",
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)

    # Parse and embed (inline — small enough for FastAPI background task)
    try:
        parser = ResumeParser()
        raw_text, parsed_data = await parser.parse(str(file_path), ext)

        resume.raw_text = raw_text
        resume.parsed_data = parsed_data.model_dump() if parsed_data else None
        resume.parse_status = "done"

        # Generate and store embedding
        embed_text = _build_embed_text(raw_text, parsed_data)
        embedding = await generate_embedding(embed_text)
        doc_id = await upsert_resume_embedding(
            user_id=user_id,
            resume_id=resume.id,
            text=embed_text,
            embedding=embedding,
            metadata={"filename": filename, "parse_status": "done"},
        )
        resume.chroma_doc_id = doc_id
        resume.chroma_collection_id = f"resumes_{str(user_id).replace('-', '_')}"

    except Exception as exc:
        logger.exception("Resume parsing failed for %s: %s", filename, exc)
        resume.parse_status = "failed"

    await db.flush()
    await db.refresh(resume)
    return resume


def _build_embed_text(raw_text: str | None, parsed_data) -> str:
    """Build a rich text representation for embedding."""
    if not parsed_data:
        return raw_text or ""

    parts = []
    if parsed_data.name:
        parts.append(f"Name: {parsed_data.name}")
    if parsed_data.skills:
        parts.append(f"Skills: {', '.join(parsed_data.skills)}")
    if parsed_data.experience:
        for exp in parsed_data.experience:
            parts.append(f"Experience: {exp.title} at {exp.company}")
            if exp.description:
                parts.append(exp.description)
    if parsed_data.education:
        for edu in parsed_data.education:
            parts.append(f"Education: {edu.degree} from {edu.institution}")

    return "\n".join(parts) or raw_text or ""


async def get_resume(db: AsyncSession, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume:
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


async def list_resumes(db: AsyncSession, user_id: uuid.UUID) -> list[Resume]:
    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())


async def get_primary_resume(db: AsyncSession, user_id: uuid.UUID) -> Resume | None:
    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id, Resume.is_primary == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def delete_resume(db: AsyncSession, resume_id: uuid.UUID, user_id: uuid.UUID) -> None:
    resume = await get_resume(db, resume_id, user_id)
    # Delete file from disk
    try:
        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)
    except Exception as exc:
        logger.warning("Could not delete resume file %s: %s", resume.file_path, exc)

    await db.delete(resume)
