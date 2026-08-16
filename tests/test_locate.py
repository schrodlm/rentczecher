"""Tests for the locate service: portal GPS first, gazetteer fallback.

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


class TestPortalGps:
    def test_portal_gps_wins_and_skips_geocoding(self, gazetteer):
        point = locate(
            _listing(lat=50.1, lon=14.43, parsed_place=ParsedPlace(names=("nesmysl",))),
            gazetteer)
        assert (point.lat, point.lon) == (50.1, 14.43)
        assert point.tier == "gps"

    def test_half_missing_gps_falls_back_to_text(self, gazetteer):
        point = locate(_listing(lat=50.1, lon=None), gazetteer)
        assert point.tier == "street"


class TestGeocodedFallback:
    def test_street_names_resolve(self, gazetteer):
        point = locate(_listing(), gazetteer)
        assert point.tier == "street"
        assert abs(point.lat - 50.10) < 0.02

    def test_unresolvable_names_yield_none(self, gazetteer):
        assert locate(
            _listing(parsed_place=ParsedPlace(names=("Nová Ves",))), gazetteer) is None

    def test_stated_district_scopes_the_lookup(self, gazetteer):
        point = locate(
            _listing(parsed_place=ParsedPlace(
                names=("Škarmanská 369 / 369",), district="Domažlice")),
            gazetteer)
        assert point.tier == "street"
        assert abs(point.lat - 49.396) < 0.01
