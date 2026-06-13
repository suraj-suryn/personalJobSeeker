import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.job import Job
from app.models.job_match import JobMatch
from app.schemas.scoring import (
    BatchScoreRequest,
    JobMatchWithDetails,
    MatchDashboard,
    MatchResult,
    ScoreJobRequest,
)

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/score", response_model=MatchResult, status_code=201)
async def score_single_job(
    body: ScoreJobRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Score a resume against a specific job. Returns match details."""
    from app.agents.match_scorer import MatchScorer
    from app.services.auth_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    scorer = MatchScorer(db)
    match = await scorer.score_job(
        user_id=user_id,
        resume_id=body.resume_id,
        job_id=body.job_id,
        provider=user.llm_provider,
    )
    return MatchResult.model_validate(match)


@router.post("/score/batch")
async def score_batch_jobs(
    body: BatchScoreRequest,
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Score a resume against multiple jobs in the background."""
    task_id = str(uuid.uuid4())

    async def _run() -> None:
        from app.database import AsyncSessionLocal
        from app.agents.match_scorer import MatchScorer
        from app.services.auth_service import get_user_by_id

        async with AsyncSessionLocal() as session:
            user = await get_user_by_id(session, user_id)
            scorer = MatchScorer(session)
            for job_id in body.job_ids:
                try:
                    await scorer.score_job(
                        user_id=user_id,
                        resume_id=body.resume_id,
                        job_id=job_id,
                        provider=user.llm_provider,
                    )
                except Exception:
                    pass  # Continue scoring remaining jobs

    background_tasks.add_task(_run)
    return {"task_id": task_id, "status": "queued", "total": len(body.job_ids)}


@router.get("/matches", response_model=MatchDashboard)
async def get_match_dashboard(
    limit: int = 50,
    min_score: float = 0,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all scored job matches with dashboard statistics."""
    result = await db.execute(
        select(JobMatch, Job)
        .join(Job, JobMatch.job_id == Job.id)
        .where(
            JobMatch.user_id == user_id,
            JobMatch.match_score >= min_score,
        )
        .order_by(desc(JobMatch.match_score))
        .limit(limit)
    )
    rows = result.all()

    matches_with_details = []
    for match, job in rows:
        matches_with_details.append(
            JobMatchWithDetails(
                match=MatchResult.model_validate(match),
                job_title=job.title,
                company=job.company,
                location=job.location,
                job_url=job.url,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                posted_at=job.posted_at,
                first_seen_at=job.first_seen_at,
            )
        )

    # Stats
    scores = [m.match.match_score for m in matches_with_details]
    all_missing = []
    for m in matches_with_details:
        all_missing.extend(m.match.missing_skills or [])
    from collections import Counter
    top_missing = [skill for skill, _ in Counter(all_missing).most_common(10)]

    return MatchDashboard(
        total_jobs=len(rows),
        scored_jobs=len(rows),
        avg_score=round(sum(scores) / len(scores), 1) if scores else 0,
        high_matches=sum(1 for s in scores if s >= 80),
        medium_matches=sum(1 for s in scores if 60 <= s < 80),
        low_matches=sum(1 for s in scores if s < 60),
        top_missing_skills=top_missing,
        matches=matches_with_details,
    )
