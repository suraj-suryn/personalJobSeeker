"""
Seed script — creates admin + sample data for testing.
Run: docker compose exec backend python -m app.utils.seed
"""

import asyncio
import logging

from app.database import AsyncSessionLocal, create_tables

logger = logging.getLogger(__name__)


async def seed() -> None:
    from app.config import get_settings
    from app.services.auth_service import ensure_admin_exists

    settings = get_settings()
    logger.info("Seeding database...")

    async with AsyncSessionLocal() as db:
        # Ensure admin exists
        await ensure_admin_exists(db)

        # Create sample jobs
        from app.models.job import Job
        from app.scrapers.base_scraper import BaseScraper

        sample_jobs = [
            {
                "title": "Senior Python Developer",
                "company": "TechCorp Inc.",
                "location": "Remote",
                "description": "We are looking for a Senior Python Developer with FastAPI, PostgreSQL, and Docker experience. You will build scalable microservices and mentor junior developers.",
                "url": "https://example.com/jobs/1",
                "url_hash": BaseScraper.make_url_hash("https://example.com/jobs/1"),
                "source": "sample",
                "salary_min": 90000,
                "salary_max": 130000,
                "salary_currency": "USD",
                "job_type": "remote",
            },
            {
                "title": "Backend Engineer - AI/ML",
                "company": "AI Startup",
                "location": "New York, NY",
                "description": "Build ML pipelines and APIs using Python, FastAPI, and LangChain. Experience with vector databases (ChromaDB, Pinecone) and LLM integration required.",
                "url": "https://example.com/jobs/2",
                "url_hash": BaseScraper.make_url_hash("https://example.com/jobs/2"),
                "source": "sample",
                "salary_min": 120000,
                "salary_max": 160000,
                "salary_currency": "USD",
                "job_type": "hybrid",
            },
            {
                "title": "Full Stack Developer",
                "company": "Product Studio",
                "location": "San Francisco, CA",
                "description": "Full stack role with React, Next.js, Python, and PostgreSQL. You'll work on consumer products with millions of users.",
                "url": "https://example.com/jobs/3",
                "url_hash": BaseScraper.make_url_hash("https://example.com/jobs/3"),
                "source": "sample",
                "salary_min": 110000,
                "salary_max": 150000,
                "salary_currency": "USD",
                "job_type": "onsite",
            },
        ]

        from sqlalchemy import select
        for job_data in sample_jobs:
            result = await db.execute(select(Job).where(Job.url_hash == job_data["url_hash"]))
            if not result.scalar_one_or_none():
                db.add(Job(**job_data))

        await db.commit()
        logger.info("Seed complete! Admin: %s / Password: %s", settings.admin_email, settings.admin_password)
        logger.info("Sample jobs created: %d", len(sample_jobs))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
