"""
Wellfound (Angel.co) Scraper — Playwright-based.
"""

import asyncio
import logging
from typing import Any

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    source_name = "wellfound"
    BASE_URL = "https://wellfound.com/jobs"

    async def search(
        self, query: str, location: str | None = None, max_results: int = 25
    ) -> list[dict[str, Any]]:
        try:
            from playwright.async_api import async_playwright

            jobs: list[dict[str, Any]] = []
            role_slug = query.lower().replace(" ", "-")
            url = f"{self.BASE_URL}?role={role_slug}"
            if location:
                url += f"&location={location.replace(' ', '%20')}"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(user_agent=self.headers["User-Agent"])
                page = await context.new_page()

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(3)

                    # Wait for job listings
                    await page.wait_for_selector('[data-test="JobListing"], .styles_component__Ue_wU', timeout=10000)
                    cards = await page.query_selector_all('[data-test="JobListing"], .styles_component__Ue_wU')

                    for card in cards[:max_results]:
                        try:
                            title_el = await card.query_selector('h2, [data-test="job-title"]')
                            company_el = await card.query_selector('h3, [data-test="company-name"]')
                            loc_el = await card.query_selector('[data-test="location"], .location')
                            link_el = await card.query_selector("a")
                            salary_el = await card.query_selector('[data-test="salary"]')

                            title = await title_el.inner_text() if title_el else ""
                            company = await company_el.inner_text() if company_el else ""
                            loc = await loc_el.inner_text() if loc_el else location or "Remote"
                            href = await link_el.get_attribute("href") if link_el else ""
                            salary_text = await salary_el.inner_text() if salary_el else ""

                            if not title or not href:
                                continue

                            if not href.startswith("http"):
                                href = "https://wellfound.com" + href

                            sal_min, sal_max, currency = self.parse_salary(salary_text)

                            jobs.append(self.normalize_job(
                                title=title.strip(),
                                company=company.strip(),
                                url=href,
                                source=self.source_name,
                                location=loc.strip(),
                                salary_min=sal_min,
                                salary_max=sal_max,
                                salary_currency=currency,
                                job_type="startup",
                            ))
                        except Exception as exc:
                            logger.debug("Skipping Wellfound card: %s", exc)

                except Exception as exc:
                    logger.warning("Wellfound scraping failed: %s", exc)
                finally:
                    await browser.close()

            logger.info("Wellfound: found %d jobs for '%s'", len(jobs), query)
            return jobs

        except Exception as exc:
            logger.error("Wellfound scraper error: %s", exc)
            return []


class NaukriScraper(BaseScraper):
    """Naukri.com scraper — httpx + BeautifulSoup4."""

    source_name = "naukri"
    BASE_URL = "https://www.naukri.com"

    async def search(
        self, query: str, location: str | None = None, max_results: int = 25
    ) -> list[dict[str, Any]]:
        query_slug = "-".join(query.lower().split())
        loc_slug = "-".join(location.lower().split()) if location else ""
        url = f"{self.BASE_URL}/{query_slug}-jobs" + (f"-in-{loc_slug}" if loc_slug else "")
        url += "?jobAge=1"  # Last 24 hours

        jobs: list[dict[str, Any]] = []

        try:
            from bs4 import BeautifulSoup

            response = await self._get(url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            cards = soup.select("article.jobTuple, div.jobTupleHeader")

            for card in cards[:max_results]:
                try:
                    title_el = card.select_one("a.title, .title")
                    company_el = card.select_one(".companyInfo a, .companyName")
                    loc_el = card.select_one(".locWdth, .location")
                    salary_el = card.select_one(".salary, .salaryText")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    href = title_el.get("href", "") if title_el else ""
                    loc = loc_el.get_text(strip=True) if loc_el else location or ""
                    salary_text = salary_el.get_text(strip=True) if salary_el else ""

                    if not title or not href:
                        continue

                    sal_min, sal_max, currency = self.parse_salary(salary_text)

                    jobs.append(self.normalize_job(
                        title=title,
                        company=company,
                        url=href,
                        source=self.source_name,
                        location=loc,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency=currency or "INR",
                    ))
                except Exception as exc:
                    logger.debug("Skipping Naukri card: %s", exc)

        except Exception as exc:
            logger.warning("Naukri scraping failed: %s", exc)

        logger.info("Naukri: found %d jobs for '%s'", len(jobs), query)
        return jobs
