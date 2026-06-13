import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class JobSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Job title or keywords")
    location: str | None = Field(None, max_length=255)
    sources: list[str] = Field(
        default=["linkedin", "indeed", "wellfound", "naukri"],
        description="Job boards to search"
    )
    experience_level: str | None = None  # entry | mid | senior
    job_type: str | None = None  # remote | onsite | hybrid
    max_results: int = Field(default=50, ge=1, le=200)


class JobResponse(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    location: str | None = None
    job_type: str | None = None
    experience_level: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    description: str | None = None
    url: str
    source: str
    posted_at: datetime | None = None
    first_seen_at: datetime
    scraped_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobSearchStatus(BaseModel):
    task_id: str
    status: str  # queued | running | done | failed
    jobs_found: int = 0
    sources_completed: list[str] = []
    message: str = ""
