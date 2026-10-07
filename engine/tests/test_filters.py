"""Tests for filtering scraped listings against a search's own constraints.

Run: python3 -m pytest tests/test_filters.py -v
"""

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria
from rentczecher_engine.services.filters import apply_filters
from tests.profiles import criteria, layouts

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


def test_max_size_excludes_larger_and_keeps_unknown():
    criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), max_size_m2=60)
    small_enough = _make_listing(id="small", size_m2=60)
    too_big = _make_listing(id="big", size_m2=70)
    unknown = _make_listing(id="unknown", size_m2=None)

    result = apply_filters([small_enough, too_big, unknown], criteria)

    assert [l.id for l in result] == ["small", "unknown"]


def test_min_land_excludes_smaller_and_keeps_unknown():
    criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), min_land_m2=200)
    big_enough = _make_listing(id="big", land_m2=300)
    too_small = _make_listing(id="small", land_m2=100)
    unknown = _make_listing(id="unknown", land_m2=None)

    result = apply_filters([big_enough, too_small, unknown], criteria)

    assert [l.id for l in result] == ["big", "unknown"]


def _layouts_kept(listing_layouts: dict[str, str | None], accepted: tuple) -> list[str]:
    listings = [_make_listing(id=listing_id, disposition_raw_text=layout)
                for listing_id, layout in listing_layouts.items()]
    return [l.id for l in apply_filters(listings, criteria(dispositions=accepted))]


def test_no_accepted_disposition_accepts_any_layout():
    kept = _layouts_kept({"two": "2+kk", "five": "5+1", "atypical": "Atypický"}, ())
    assert kept == ["two", "five", "atypical"]


def test_only_an_accepted_disposition_passes():
    kept = _layouts_kept({"two": "2+kk", "three": "3+1", "four": "4+kk"}, layouts("2+kk", "4+kk"))
    assert kept == ["two", "four"]


def test_a_studio_passes_as_an_accepted_1kk():
    assert _layouts_kept({"studio": "Garsoniéra", "one-separate": "1+1"}, layouts("1+kk")) == ["studio"]


def test_a_listing_stating_no_layout_passes():
    """A layout the listing does not state, or a label naming no layout,
    gives nothing to mismatch."""
    assert _layouts_kept({"missing": None, "building": "Rodinný"}, layouts("2+kk")) == ["missing", "building"]


def test_an_atypical_layout_passes_only_when_accepted():
    assert _layouts_kept({"atypical": "Atypický"}, layouts("2+kk")) == []
    assert _layouts_kept({"atypical": "Atypický"}, layouts("2+kk", "atypicky")) == ["atypical"]


def test_filters_combine():
    keeper = _make_listing(id="keeper", size_m2=50, land_m2=300)
    too_little_land = _make_listing(id="little-land", size_m2=50, land_m2=100)
    too_small = _make_listing(id="too-small", size_m2=30, land_m2=300)
    unaccepted_layout = _make_listing(id="unaccepted-layout", size_m2=50, land_m2=300, disposition_raw_text="3+1")

    result = apply_filters([keeper, too_little_land, too_small, unaccepted_layout],
                           criteria(min_size_m2=40, min_land_m2=200, dispositions=layouts("2+kk", "2+1")))

    assert [l.id for l in result] == ["keeper"]
