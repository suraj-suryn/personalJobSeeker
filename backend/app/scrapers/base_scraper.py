"""
Base scraper — shared utilities for all job board scrapers.
"""

import hashlib
import logging
import random
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class BaseScraper(ABC):
    source_name: str = "unknown"

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }

    @abstractmethod
    async def search(
        self, query: str, location: str | None, max_results: int
    ) -> list[dict[str, Any]]:
        """Search for jobs and return list of job dicts."""
        ...

    @staticmethod
    def make_url_hash(url: str) -> str:
        """SHA256 of normalized URL for deduplication."""
        normalized = url.lower().strip().rstrip("/")
        # Strip tracking params
        normalized = re.sub(r"[?&](utm_[^&]*|ref=[^&]*|source=[^&]*)", "", normalized)
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def normalize_job(
        *,
        title: str,
        company: str,
        url: str,
        source: str,
        description: str | None = None,
        location: str | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        salary_currency: str | None = None,
        job_type: str | None = None,
        experience_level: str | None = None,
        posted_at: datetime | None = None,
    ) -> dict[str, Any]:
        return {
            "title": title.strip()[:500],
            "company": company.strip()[:255],
            "url": url.strip(),
            "url_hash": BaseScraper.make_url_hash(url),
            "source": source,
            "description": description,
            "location": location,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "job_type": job_type,
            "experience_level": experience_level,
            "posted_at": posted_at,
            "scraped_at": datetime.now(timezone.utc),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=15))
    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(
            headers=self.headers,
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            return await client.get(url, params=params)

    @staticmethod
    def parse_salary(salary_text: str) -> tuple[float | None, float | None, str | None]:
        """Extract min, max salary and currency from text like '$80,000 - $120,000'."""
        if not salary_text:
            return None, None, None

        currency = None
        if "$" in salary_text:
            currency = "USD"
        elif "£" in salary_text:
            currency = "GBP"
        elif "€" in salary_text:
            currency = "EUR"
        elif "₹" in salary_text:
            currency = "INR"

        numbers = re.findall(r"[\d,]+", salary_text.replace(",", ""))
        nums = [float(n.replace(",", "")) for n in numbers if n]

        if len(nums) >= 2:
            return min(nums), max(nums), currency
        elif len(nums) == 1:
            return nums[0], nums[0], currency
        return None, None, currency
