"""
APScheduler-based job scheduler for recurring tasks.
Runs inside the FastAPI process — no separate worker needed.

Scheduled tasks:
  - Every N minutes: search for new jobs across all boards
  - Daily 8am: send email digest to all users
"""

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler(timezone="UTC")


async def _run_job_search() -> None:
    """Background task: run job search for all active users' saved search preferences."""
    try:
        from app.database import AsyncSessionLocal
        from app.agents.job_search_agent import JobSearchAgent
        from app.services.notification_service import send_new_jobs_notification

        async with AsyncSessionLocal() as db:
            agent = JobSearchAgent(db)
            new_jobs = await agent.run_scheduled_search()
            if new_jobs:
                await send_new_jobs_notification(db, new_jobs)
                logger.info("Scheduled search found %d new jobs", len(new_jobs))
    except Exception as exc:
        logger.exception("Scheduled job search failed: %s", exc)


async def _run_daily_digest() -> None:
    """Daily email digest: summary of top matching jobs."""
    try:
        from app.database import AsyncSessionLocal
        from app.services.email_service import send_daily_digest

        async with AsyncSessionLocal() as db:
            await send_daily_digest(db)
            logger.info("Daily digest sent")
    except Exception as exc:
        logger.exception("Daily digest failed: %s", exc)


def start_scheduler() -> None:
    """Register all jobs and start the scheduler."""
    # Recurring job search (every N minutes, configurable)
    scheduler.add_job(
        _run_job_search,
        trigger=IntervalTrigger(minutes=settings.job_search_interval_minutes),
        id="job_search",
        name="Recurring Job Search",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Daily email digest at 8:00 AM UTC
    scheduler.add_job(
        _run_daily_digest,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_digest",
        name="Daily Email Digest",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info(
        "Scheduler started — job search every %d min, daily digest at 08:00 UTC",
        settings.job_search_interval_minutes,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def trigger_job_search_now() -> None:
    """Manually trigger a job search immediately (called from API)."""
    scheduler.add_job(
        _run_job_search,
        id="job_search_manual",
        name="Manual Job Search",
        replace_existing=True,
    )
