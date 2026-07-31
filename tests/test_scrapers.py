"""Offline scraper behavior tests — no network access.

Run: python3 -m pytest tests/test_scrapers.py -v
"""

from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher.adapters.scrapers.remax import RemaxScraper
from rentczecher.adapters.scrapers.sreality import SrealityScraper


class TestScraperEnabledFlag:
    """A scraper whose config block is absent or lacks enabled:true never runs,
    even when instantiated directly."""

    def test_scrapers_are_disabled_by_default(self):
        profile = {"search": {"max_price": 25000}, "scrapers": {}}
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper):
            assert scraper_cls(profile).scrape() == [], scraper_cls.name


class TestRemaxUrlBuilding:
    """_build_url() substitutes min/max price into the config template."""

    def test_url_building(self):
        profile = {
            "search": {"min_price": 17000, "max_price": 25000},
            "scrapers": {"remax": {
                "enabled": True,
                "search_url": (
                    "https://www.remax-czech.cz/reality/vyhledavani/"
                    "?hledani=2&price_from={min_price}&price_to={max_price}"
                ),
            }},
        }
        url = RemaxScraper(profile)._build_url()
        assert "price_from=17000" in url
        assert "price_to=25000" in url
        assert "{min_price}" not in url and "{max_price}" not in url


class TestSrealityDistrictConfig:
    """A sreality profile without locality_district_id logs an error and yields
    no results instead of another region's listings."""

    def test_missing_district_id_logs_error_and_returns_nothing(self, caplog):
        profile = {
            "search": {"max_price": 25000},
            "scrapers": {"sreality": {
                "enabled": True,
                "category_main_cb": 1,
                "category_type_cb": 2,
            }},
        }
        with caplog.at_level("ERROR", logger="byt_watchdog"):
            listings = SrealityScraper(profile).scrape()
        assert listings == []
        assert any("locality_district_id" in r.message for r in caplog.records)
