"""Tests for the locate service: a listing's place comes from its text.

Run: python3 -m pytest tests/test_locate.py -v
"""

import pytest

from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import ParsedPlace
from rentczecher_engine.services.locate import locate, locate_listings


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


def _listing(parsed_place=ParsedPlace(names=("Veletržní", "Praha 7")), **kw):
    return Listing.build(id="sreality:1", source="sreality", title="t", price=20000,
                         location="l", parsed_place=parsed_place, url="u", **kw)


class TestLocate:
    def test_text_resolution_supplies_the_location(self, gazetteer):
        location = locate(_listing(), gazetteer)
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Praha"

    def test_ambiguous_text_stays_unlocated_even_with_gps(self, gazetteer):
        """A GPS point never stands in for a place the text does not name."""
        location = locate(_listing(lat=50.1, lon=14.43,
                                   parsed_place=ParsedPlace(names=("Nová Ves",))), gazetteer)
        assert location is None

    def test_ambiguous_text_without_gps_has_no_location(self, gazetteer):
        location = locate(_listing(parsed_place=ParsedPlace(names=("Nová Ves",))), gazetteer)
        assert location is None

    def test_stated_district_scopes_the_lookup(self, gazetteer):
        location = locate(_listing(parsed_place=ParsedPlace(
            names=("Škarmanská 369 / 369",), district="Domažlice")), gazetteer)
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Kdyně"


class TestLocateListings:
    def test_every_listing_comes_back_with_its_location_annotation(self, gazetteer):
        locatable = _listing()
        unlocatable = _listing(parsed_place=ParsedPlace(names=("Nová Ves",)))

        located = locate_listings([locatable, unlocatable], gazetteer)

        assert located[0].resolved_location is not None
        assert located[0].resolved_location.obec.name == "Praha"
        assert located[1].resolved_location is None
