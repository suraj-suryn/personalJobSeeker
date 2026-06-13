import logging
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

logger = logging.getLogger(__name__)


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job:
    from fastapi import HTTPException, status
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


async def list_jobs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    query: str | None = None,
    source: str | None = None,
    location: str | None = None,
) -> tuple[list[Job], int]:
    """List jobs with optional text filter + pagination."""
    stmt = select(Job)

    if query:
        like = f"%{query}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(like),
                Job.company.ilike(like),
                Job.description.ilike(like),
            )
        )
    if source:
        stmt = stmt.where(Job.source == source)
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))

    total_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = total_result.scalar_one()

    stmt = stmt.order_by(Job.first_seen_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    jobs = list(result.scalars().all())
    return jobs, total


async def bulk_upsert_jobs(db: AsyncSession, jobs_data: list[dict]) -> tuple[int, int]:
    """
    Upsert a batch of scraped jobs.
    Uses url_hash for deduplication.
    Returns (inserted, skipped).
    """
    inserted = 0
    skipped = 0

    for data in jobs_data:
        url_hash = data.get("url_hash")
        if not url_hash:
            continue

        result = await db.execute(select(Job).where(Job.url_hash == url_hash))
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        job = Job(**{k: v for k, v in data.items() if hasattr(Job, k)})
        db.add(job)
        inserted += 1

    if inserted:
        await db.flush()

    return inserted, skipped


async def get_recent_jobs(db: AsyncSession, hours: int = 6, limit: int = 50) -> list[Job]:
    """Get jobs posted or first seen within the last N hours."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(Job)
        .where(Job.first_seen_at >= cutoff)
        .order_by(Job.first_seen_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
