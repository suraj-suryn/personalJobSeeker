from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.documents import cover_letter_router, outreach_router
from app.api.v1.applications import router as applications_router
from app.api.v1.automation import router as automation_router
from app.api.v1.interview_prep import router as interview_prep_router

__all__ = [
    "auth_router",
    "resumes_router",
    "jobs_router",
    "scoring_router",
    "cover_letter_router",
    "outreach_router",
    "applications_router",
    "automation_router",
    "interview_prep_router",
]
