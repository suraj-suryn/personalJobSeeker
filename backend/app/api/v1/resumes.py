import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.schemas.resume import (
    GenerateResumeVersionRequest,
    ResumeResponse,
    ResumeUploadResponse,
    ResumeVersionResponse,
)
from app.services.resume_service import (
    delete_resume,
    get_resume,
    list_resumes,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(
    file: Annotated[UploadFile, File(description="PDF or DOCX resume file")],
    is_primary: Annotated[bool, Form()] = False,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume file. Triggers background LLM parsing."""
    from app.services.resume_service import save_and_parse_resume
    resume = await save_and_parse_resume(db, user_id, file, is_primary)
    return ResumeUploadResponse.model_validate(resume)


@router.get("/", response_model=list[ResumeResponse])
async def list_my_resumes(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all resumes for the current user."""
    resumes = await list_resumes(db, user_id)
    return [ResumeResponse.model_validate(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_my_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    resume = await get_resume(db, resume_id, user_id)
    return ResumeResponse.model_validate(resume)


@router.delete("/{resume_id}", status_code=204)
async def delete_my_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await delete_resume(db, resume_id, user_id)


# ─── Resume Versions (ATS Optimized) ──────────────────────────────────────

@router.post("/versions/generate", response_model=ResumeVersionResponse, status_code=201)
async def generate_optimized_resume(
    body: GenerateResumeVersionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate an ATS-optimized resume version for a specific job."""
    from app.agents.resume_optimizer import ResumeOptimizer
    from app.services.auth_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    optimizer = ResumeOptimizer(db)
    version = await optimizer.optimize(
        user_id=user_id,
        resume_id=body.resume_id,
        job_id=body.job_id,
        provider=user.llm_provider,
    )
    return ResumeVersionResponse.model_validate(version)


@router.get("/versions/{version_id}/download/{fmt}")
async def download_resume_version(
    version_id: uuid.UUID,
    fmt: str,  # pdf | docx
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Download optimized resume as PDF or DOCX."""
    from sqlalchemy import select
    from app.models.resume_version import ResumeVersion

    result = await db.execute(
        select(ResumeVersion).where(
            ResumeVersion.id == version_id,
            ResumeVersion.user_id == user_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        from fastapi import HTTPException
        raise HTTPException(404, "Version not found")

    if fmt == "pdf" and version.file_path_pdf and Path(version.file_path_pdf).exists():
        return FileResponse(version.file_path_pdf, media_type="application/pdf", filename=f"resume_{version_id}.pdf")
    elif fmt == "docx" and version.file_path_docx and Path(version.file_path_docx).exists():
        return FileResponse(
            version.file_path_docx,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"resume_{version_id}.docx",
        )
    from fastapi import HTTPException
    raise HTTPException(404, "File not found")
