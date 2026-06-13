import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    notes: str | None = None
    platform: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None
    platform: str | None = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    status: ApplicationStatus
    applied_at: datetime | None = None
    notes: str | None = None
    platform: str | None = None
    created_at: datetime
    updated_at: datetime

    # Job details for convenience
    job_title: str | None = None
    company: str | None = None
    job_url: str | None = None

    model_config = {"from_attributes": True}


class CoverLetterGenerateRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID
    tone: str = Field(default="professional", pattern="^(professional|enthusiastic|concise)$")


class CoverLetterResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    content: str | None = None
    tone: str
    file_path_pdf: str | None = None
    file_path_docx: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutreachGenerateRequest(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID
    message_type: str = Field(..., pattern="^(linkedin_message|email_draft|follow_up)$")
    recipient_name: str | None = None


class OutreachResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    message_type: str
    content: str | None = None
    subject: str | None = None
    recipient_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
