"""Tests for the per-scraper orchestration loop.

Run: python3 -m pytest tests/test_scrape.py -v
"""

import pytest

from rentczecher.domain.errors import PlaceNotFoundError, ScraperBrokenError
from rentczecher.domain.listing import Listing
from rentczecher.domain.search import SearchSpec
from rentczecher.services.scrape import scrape_all

SPEC = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7")


def _make_listing(**kwargs):
    defaults = dict(
        id="sreality:1",
        source="sreality",
        title="Prodej domu 120 m2",
        price=3_000_000,
        location="Nekvasovy, okres Plzeň-jih",
        url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


class WorkingScraper:
    def __init__(self, spec, client):
        pass

    def scrape(self):
        return [_make_listing()]


class EmptyScraper:
    def __init__(self, spec, client):
        pass

    def scrape(self):
        return []


class BrokenScraper:
    def __init__(self, spec, client):
        pass

    def scrape(self):
        raise ScraperBrokenError("bezrealitky: __NEXT_DATA__ payload missing from search page")


class CrashingScraper:
    def __init__(self, spec, client):
        pass

    def scrape(self):
        raise ValueError("boom")


class UnresolvablePlaceScraper:
    def __init__(self, spec, client):
        raise PlaceNotFoundError(spec.place, ())


def test_a_working_scraper_is_recorded_ok_with_its_listing_count():
    listings, health = scrape_all({"sreality": WorkingScraper}, SPEC, client=None)
    assert [l.id for l in listings] == ["sreality:1"]
    assert health["sreality"].status == "ok"
    assert health["sreality"].error is None
    assert health["sreality"].listing_count == 1


def test_zero_results_are_recorded_distinctly_from_a_broken_scraper():
    listings, health = scrape_all({"sreality": EmptyScraper}, SPEC, client=None)
    assert listings == []
    assert health["sreality"].status == "zero_results"
    assert health["sreality"].listing_count == 0


def test_a_scraper_broken_error_is_recorded_with_its_error_text_and_does_not_raise():
    listings, health = scrape_all({"bezrealitky": BrokenScraper}, SPEC, client=None)
    assert listings == []
    assert health["bezrealitky"].status == "broken"
    assert "__NEXT_DATA__" in health["bezrealitky"].error


def test_a_generic_exception_is_isolated_and_recorded_as_broken(caplog):
    with caplog.at_level("ERROR", logger="rentczecher"):
        listings, health = scrape_all({"sreality": CrashingScraper}, SPEC, client=None)
    assert listings == []
    assert health["sreality"].status == "broken"
    assert any(r.exc_info for r in caplog.records), "a generic failure logs its traceback"


def test_one_broken_scraper_does_not_prevent_others_listings():
    listings, health = scrape_all(
        {"sreality": WorkingScraper, "bezrealitky": BrokenScraper}, SPEC, client=None,
    )
    assert [l.id for l in listings] == ["sreality:1"]
    assert health["sreality"].status == "ok"
    assert health["bezrealitky"].status == "broken"


def test_place_not_found_error_propagates_instead_of_being_isolated():
    with pytest.raises(PlaceNotFoundError):
        scrape_all({"sreality": UnresolvablePlaceScraper}, SPEC, client=None)
