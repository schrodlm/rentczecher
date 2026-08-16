"""Tests for the locate service: text resolution first, geometry as fallback.

Run: python3 -m pytest tests/test_locate.py -v
"""

import pytest

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.domain.listing import Listing
from rentczecher.domain.location import ParsedPlace
from rentczecher.services.locate import locate


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


def _listing(parsed_place=ParsedPlace(names=("Veletržní", "Praha 7")), **kw):
    return Listing.build(id="sreality:1", source="sreality", title="t", price=20000,
                         location="l", parsed_place=parsed_place, url="u", **kw)


class TestLocate:
    def test_text_resolution_supplies_the_place(self, gazetteer):
        place = locate(_listing(), gazetteer)
        assert place.tier == "street"
        assert place.muni_name == "Praha"

    def test_ambiguous_text_with_gps_reverse_geocodes(self, gazetteer):
        place = locate(_listing(lat=50.1, lon=14.43,
                                 parsed_place=ParsedPlace(names=("Nová Ves",))), gazetteer)
        assert place.muni_name == "Praha"
        assert place.tier in ("municipality_part", "municipality")

    def test_ambiguous_text_without_gps_has_no_place(self, gazetteer):
        place = locate(_listing(parsed_place=ParsedPlace(names=("Nová Ves",))), gazetteer)
        assert place is None

    def test_gps_outside_any_municipality_is_noise(self, gazetteer):
        place = locate(_listing(lat=40.0, lon=10.0,
                                 parsed_place=ParsedPlace(names=("blbost",))), gazetteer)
        assert place is None

    def test_stated_district_scopes_the_lookup(self, gazetteer):
        place = locate(_listing(parsed_place=ParsedPlace(
            names=("Škarmanská 369 / 369",), district="Domažlice")), gazetteer)
        assert place.tier == "street"
        assert place.muni_name == "Kdyně"
