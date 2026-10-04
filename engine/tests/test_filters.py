"""Tests for filtering scraped listings against a search's own constraints.

Run: python3 -m pytest tests/test_filters.py -v
"""

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria
from rentczecher_engine.services.filters import apply_filters

CRITERIA = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="sreality:1", source="sreality", title="Pronájem bytu 2+kk 50 m²",
        price=20000, location_raw_text="Veletržní, Praha 7", url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def test_no_constraints_passes_everything_through():
    listings = [_make_listing(disposition_raw_text="2+kk"), _make_listing(id="a", disposition_raw_text=None)]
    assert apply_filters(listings, CRITERIA) == listings


def test_min_size_excludes_smaller_and_keeps_unknown():
    criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), min_size_m2=40)
    big_enough = _make_listing(id="big", size_m2=50)
    too_small = _make_listing(id="small", size_m2=30)
    unknown = _make_listing(id="unknown", size_m2=None)

    result = apply_filters([big_enough, too_small, unknown], criteria)

    assert [l.id for l in result] == ["big", "unknown"]


def test_min_land_excludes_smaller_and_keeps_unknown():
    criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), min_land_m2=200)
    big_enough = _make_listing(id="big", land_m2=300)
    too_small = _make_listing(id="small", land_m2=100)
    unknown = _make_listing(id="unknown", land_m2=None)

    result = apply_filters([big_enough, too_small, unknown], criteria)

    assert [l.id for l in result] == ["big", "unknown"]


def test_filters_combine():
    criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78),
                        min_size_m2=40, min_land_m2=200)
    keeper = _make_listing(id="keeper", size_m2=50, land_m2=300)
    too_little_land = _make_listing(id="little-land", size_m2=50, land_m2=100)
    too_small = _make_listing(id="too-small", size_m2=30, land_m2=300)

    result = apply_filters([keeper, too_little_land, too_small], criteria)

    assert [l.id for l in result] == ["keeper"]
