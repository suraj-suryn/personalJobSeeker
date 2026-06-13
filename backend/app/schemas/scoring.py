import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScoreJobRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID


class BatchScoreRequest(BaseModel):
    resume_id: uuid.UUID
    job_ids: list[uuid.UUID] = Field(..., max_length=100)


class MatchResult(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    match_score: float
    cosine_score: float | None = None
    missing_skills: list[str] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobMatchWithDetails(BaseModel):
    match: MatchResult
    job_title: str
    company: str
    location: str | None = None
    job_url: str
    salary_min: float | None = None
    salary_max: float | None = None
    posted_at: datetime | None = None
    first_seen_at: datetime


class MatchDashboard(BaseModel):
    total_jobs: int
    scored_jobs: int
    avg_score: float
    high_matches: int  # score >= 80
    medium_matches: int  # score 60-79
    low_matches: int  # score < 60
    top_missing_skills: list[str]
    matches: list[JobMatchWithDetails]
