import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db

router = APIRouter(prefix="/interview-prep", tags=["interview-prep"])


@router.post("/generate")
async def generate_interview_prep(
    job_id: uuid.UUID,
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate interview preparation materials for a specific job:
    - Technical questions with suggested answers
    - Behavioral questions (STAR format)
    - Company-specific questions
    - Questions to ask the interviewer
    - Key talking points
    """
    from app.agents.interview_prep_agent import InterviewPrepAgent
    from app.services.auth_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    agent = InterviewPrepAgent(db)
    prep = await agent.generate_prep(
        user_id=user_id,
        resume_id=resume_id,
        job_id=job_id,
        provider=user.llm_provider,
    )
    return prep
