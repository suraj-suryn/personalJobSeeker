import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_year: str | None = None
    end_year: str | None = None
    gpa: str | None = None


class ExperienceItem(BaseModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] = []


class ProjectItem(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = []
    url: str | None = None


class CertificationItem(BaseModel):
    name: str | None = None
    issuer: str | None = None
    year: str | None = None
    url: str | None = None


class ParsedResumeData(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    parse_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    is_primary: bool
    parse_status: str
    parsed_data: dict[str, Any] | None = None
    chroma_doc_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeVersionResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID
    optimized_content: dict[str, Any] | None = None
    changes_summary: str | None = None
    file_path_pdf: str | None = None
    file_path_docx: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateResumeVersionRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID
