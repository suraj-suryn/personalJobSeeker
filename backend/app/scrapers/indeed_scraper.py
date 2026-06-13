"""
Indeed Job Scraper — uses httpx + BeautifulSoup4.
"""

import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    source_name = "indeed"
    BASE_URL = "https://www.indeed.com/jobs"

    async def search(
        self, query: str, location: str | None = None, max_results: int = 25
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": query,
            "fromage": "1",   # Last 24 hours
            "sort": "date",
        }
        if location:
            params["l"] = location

        jobs: list[dict[str, Any]] = []
        start = 0

        while len(jobs) < max_results:
            params["start"] = start
            try:
                response = await self._get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    logger.warning("Indeed returned status %d", response.status_code)
                    break

                soup = BeautifulSoup(response.text, "lxml")
                cards = soup.select("div.job_seen_beacon, div[data-jk]")

                if not cards:
                    break

                for card in cards:
                    try:
                        job = self._parse_card(card, location)
                        if job:
                            jobs.append(job)
                    except Exception as exc:
                        logger.debug("Skipping Indeed card: %s", exc)

                # Pagination
                next_btn = soup.select_one('a[data-testid="pagination-page-next"]')
                if not next_btn:
                    break
                start += 10

            except Exception as exc:
                logger.warning("Indeed scraping error: %s", exc)
                break

        logger.info("Indeed: found %d jobs for '%s'", len(jobs), query)
        return jobs[:max_results]

    def _parse_card(self, card, default_location: str | None) -> dict[str, Any] | None:
        # Job title and URL
        title_el = card.select_one("h2.jobTitle a, a[data-jk]")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if not href:
            return None
        if not href.startswith("http"):
            href = "https://www.indeed.com" + href

        # Company
        company_el = card.select_one('[data-testid="company-name"], .companyName')
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # Location
        loc_el = card.select_one('[data-testid="text-location"], .companyLocation')
        location = loc_el.get_text(strip=True) if loc_el else default_location

        # Salary
        salary_el = card.select_one('[data-testid="attribute_snippet_testid"], .salary-snippet')
        salary_text = salary_el.get_text(strip=True) if salary_el else ""
        sal_min, sal_max, currency = self.parse_salary(salary_text)

        # Description snippet
        desc_el = card.select_one(".job-snippet, .underShelfFooter ul")
        description = desc_el.get_text(strip=True) if desc_el else None

        # Date
        date_el = card.select_one('[data-testid="myJobsStateDate"], .date')
        posted_at = self._parse_relative_date(date_el.get_text(strip=True) if date_el else "")

        return self.normalize_job(
            title=title,
            company=company,
            url=href,
            source=self.source_name,
            description=description,
            location=location,
            salary_min=sal_min,
            salary_max=sal_max,
            salary_currency=currency,
            posted_at=posted_at,
        )

    @staticmethod
    def _parse_relative_date(text: str) -> datetime | None:
        """Convert 'Posted 2 days ago' → datetime."""
        now = datetime.now(timezone.utc)
        text = text.lower()
        if "just posted" in text or "today" in text:
            return now
        if "hour" in text:
            import re
            m = re.search(r"(\d+)", text)
            if m:
                return now - timedelta(hours=int(m.group(1)))
        if "day" in text:
            import re
            m = re.search(r"(\d+)", text)
            if m:
                return now - timedelta(days=int(m.group(1)))
        return None
