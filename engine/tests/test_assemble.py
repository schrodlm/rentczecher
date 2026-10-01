"""Tests for building a PropertyIdentity from a located listing.

Run: python3 -m pytest tests/test_assemble.py -v
"""

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.location import ResolvedPlace
from rentczecher.services.assemble import assemble_property

CREATED_AT = "2026-08-13T06:00:00+00:00"


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test:1", source="test", title="Byt 2+kk", price=20000,
        location="Praha 7 - Holešovice", url="https://example.com",
        size_m2=50, disposition="2+kk", land_m2=120,
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def test_uses_listings_own_gps_when_present():
    listing = _make_listing(lat=50.1, lon=14.4)

    identity = assemble_property(listing, property_id="prop-1", created_at=CREATED_AT)

    assert identity.id == "prop-1"
    assert identity.created_at == CREATED_AT
    assert identity.title == "Byt 2+kk"
    assert identity.location == "Praha 7 - Holešovice"
    assert identity.size_m2 == 50
    assert identity.disposition == "2+kk"
    assert identity.land_m2 == 120
    assert identity.lat == 50.1
    assert identity.lon == 14.4


def test_falls_back_to_the_resolved_places_centroid_when_no_gps():
    place = ResolvedPlace(name="Holešovice", muni_name="Praha", okres_name=None,
                           tier="city_district", lat=50.09, lon=14.42)
    listing = _make_listing(lat=None, lon=None, place=place)

    identity = assemble_property(listing, property_id="prop-1", created_at=CREATED_AT)

    assert identity.lat == 50.09
    assert identity.lon == 14.42


def test_neither_gps_nor_place_leaves_coordinates_none():
    listing = _make_listing(lat=None, lon=None)

    identity = assemble_property(listing, property_id="prop-1", created_at=CREATED_AT)

    assert identity.lat is None
    assert identity.lon is None
