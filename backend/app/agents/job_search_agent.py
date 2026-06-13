"""
Job Search Agent — orchestrates all scrapers and saves results to the database.
"""

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.job_service import bulk_upsert_jobs

logger = logging.getLogger(__name__)
settings = get_settings()


class JobSearchAgent:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        query: str,
        location: str | None = None,
        sources: list[str] | None = None,
        max_per_source: int | None = None,
    ) -> tuple[int, int]:
        """
        Search across all specified job boards.
        Returns (inserted, skipped) counts.
        """
        if sources is None:
            sources = ["linkedin", "indeed", "wellfound", "naukri"]

        max_results = max_per_source or settings.max_jobs_per_search
        tasks = []

        scraper_map = {
            "linkedin": self._scrape_linkedin,
            "indeed": self._scrape_indeed,
            "wellfound": self._scrape_wellfound,
            "naukri": self._scrape_naukri,
        }

        for source in sources:
            if source in scraper_map:
                tasks.append(scraper_map[source](query, location, max_results))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Scraper %s failed: %s", sources[i] if i < len(sources) else "?", result)
            elif isinstance(result, list):
                all_jobs.extend(result)

        if not all_jobs:
            return 0, 0

        inserted, skipped = await bulk_upsert_jobs(self.db, all_jobs)
        logger.info("Job search '%s': inserted=%d, skipped=%d", query, inserted, skipped)
        return inserted, skipped

    async def run_scheduled_search(self) -> list:
        """
        Called by APScheduler. Searches for jobs using all users' saved preferences
        and returns newly inserted Job ORM objects.
        """
        from sqlalchemy import select
        from app.models.job import Job
        from app.services.job_service import get_recent_jobs

        # For a personal app — use default search terms from settings
        # In future: per-user saved searches
        default_queries = ["software engineer", "python developer", "backend developer"]
        total_inserted = 0

        for q in default_queries:
            inserted, _ = await self.search(q, max_per_source=20)
            total_inserted += inserted

        if total_inserted:
            new_jobs = await get_recent_jobs(self.db, hours=1)
            return new_jobs
        return []

    async def _scrape_linkedin(
        self, query: str, location: str | None, max_results: int
    ) -> list[dict]:
        from app.scrapers.linkedin_scraper import LinkedInScraper
        scraper = LinkedInScraper()
        return await scraper.search(query=query, location=location, max_results=max_results)

    async def _scrape_indeed(
        self, query: str, location: str | None, max_results: int
    ) -> list[dict]:
        from app.scrapers.indeed_scraper import IndeedScraper
        scraper = IndeedScraper()
        return await scraper.search(query=query, location=location, max_results=max_results)

    async def _scrape_wellfound(
        self, query: str, location: str | None, max_results: int
    ) -> list[dict]:
        from app.scrapers.wellfound_scraper import WellfoundScraper
        scraper = WellfoundScraper()
        return await scraper.search(query=query, location=location, max_results=max_results)

    async def _scrape_naukri(
        self, query: str, location: str | None, max_results: int
    ) -> list[dict]:
        from app.scrapers.naukri_scraper import NaukriScraper
        scraper = NaukriScraper()
        return await scraper.search(query=query, location=location, max_results=max_results)
