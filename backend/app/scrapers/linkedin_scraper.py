"""
LinkedIn Job Scraper — uses Playwright with stealth to scrape public job listings.

Note: LinkedIn aggressively blocks scrapers. Best results when:
  1. Running from a residential IP
  2. Using the LI_AT_COOKIE env var (your LinkedIn session cookie)

For reliable results, set LI_AT_COOKIE in your .env file.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    source_name = "linkedin"
    BASE_URL = "https://www.linkedin.com/jobs/search"

    async def search(
        self, query: str, location: str | None = None, max_results: int = 25
    ) -> list[dict[str, Any]]:
        """Scrape LinkedIn job listings using Playwright."""
        try:
            from playwright.async_api import async_playwright

            params = {
                "keywords": query,
                "f_TPR": "r3600",   # Posted in last hour
                "sortBy": "DD",     # Most recent first
            }
            if location:
                params["location"] = location

            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{self.BASE_URL}?{query_str}"

            jobs: list[dict[str, Any]] = []

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    viewport={"width": 1280, "height": 800},
                )

                # Inject session cookie if available
                li_at = os.getenv("LI_AT_COOKIE", "")
                if li_at:
                    await context.add_cookies([{
                        "name": "li_at",
                        "value": li_at,
                        "domain": ".linkedin.com",
                        "path": "/",
                    }])

                page = await context.new_page()

                # Remove automation fingerprints
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2)

                    # Wait for job cards
                    await page.wait_for_selector(".job-search-card, .jobs-search__results-list li", timeout=10000)

                    job_cards = await page.query_selector_all(".job-search-card, .jobs-search__results-list li")

                    for card in job_cards[:max_results]:
                        try:
                            title_el = await card.query_selector("h3, .job-search-card__title")
                            company_el = await card.query_selector("h4, .job-search-card__subtitle")
                            location_el = await card.query_selector(".job-search-card__location")
                            link_el = await card.query_selector("a")
                            time_el = await card.query_selector("time")

                            title = await title_el.inner_text() if title_el else ""
                            company = await company_el.inner_text() if company_el else ""
                            loc = await location_el.inner_text() if location_el else ""
                            href = await link_el.get_attribute("href") if link_el else ""
                            posted_str = await time_el.get_attribute("datetime") if time_el else None

                            if not title or not href:
                                continue

                            # Clean job URL (remove tracking params)
                            job_url = href.split("?")[0] if href else ""
                            if not job_url.startswith("http"):
                                job_url = "https://www.linkedin.com" + job_url

                            posted_at = None
                            if posted_str:
                                try:
                                    posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
                                except ValueError:
                                    pass

                            jobs.append(self.normalize_job(
                                title=title.strip(),
                                company=company.strip(),
                                url=job_url,
                                source=self.source_name,
                                location=loc.strip() or location,
                                posted_at=posted_at,
                            ))
                        except Exception as exc:
                            logger.debug("Skipping LinkedIn card: %s", exc)

                except Exception as exc:
                    logger.warning("LinkedIn scraping failed: %s", exc)
                finally:
                    await browser.close()

            logger.info("LinkedIn: found %d jobs for '%s'", len(jobs), query)
            return jobs

        except Exception as exc:
            logger.error("LinkedIn scraper error: %s", exc)
            return []
