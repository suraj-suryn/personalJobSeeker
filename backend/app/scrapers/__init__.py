from app.scrapers.base_scraper import BaseScraper
from app.scrapers.linkedin_scraper import LinkedInScraper
from app.scrapers.indeed_scraper import IndeedScraper
from app.scrapers.wellfound_scraper import WellfoundScraper, NaukriScraper

__all__ = [
    "BaseScraper",
    "LinkedInScraper",
    "IndeedScraper",
    "WellfoundScraper",
    "NaukriScraper",
]
