"""Offline scraper behavior tests — no network access.

Run: python3 -m pytest tests/test_scrapers.py -v
"""

from scrapers.bezrealitky import BezrealitkyScraper
from scrapers.remax import RemaxScraper
from scrapers.sreality import SrealityScraper


class TestScraperEnabledFlag:
    """A scraper whose config block is absent or lacks enabled:true never runs,
    even when instantiated directly."""

    def test_scrapers_are_disabled_by_default(self):
        profile = {"search": {"max_price": 25000}, "scrapers": {}}
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper):
            assert scraper_cls(profile).scrape() == [], scraper_cls.name
