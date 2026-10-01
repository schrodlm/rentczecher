"""Tests for filtering scraped listings against a search's own constraints.

Run: python3 -m pytest tests/test_filters.py -v
"""

from rentczecher.domain.listing import Listing
from rentczecher.domain.search import SearchSpec
from rentczecher.services.filters import apply_filters

SPEC = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7")


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="sreality:1", source="sreality", title="Pronájem bytu 2+kk 50 m²",
        price=20000, location="Veletržní, Praha 7", url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def test_no_constraints_passes_everything_through():
    listings = [_make_listing(disposition="2+kk"), _make_listing(id="a", disposition=None)]
    assert apply_filters(listings, SPEC) == listings


def test_disposition_filter_excludes_non_matching_and_keeps_unknown():
    spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7",
                      dispositions=("2+kk",))
    matching = _make_listing(id="match", disposition="2+kk")
    other = _make_listing(id="other", disposition="3+1")
    unknown = _make_listing(id="unknown", disposition=None)

    result = apply_filters([matching, other, unknown], spec)

    assert [l.id for l in result] == ["match", "unknown"]


def test_disposition_filter_is_case_insensitive():
    spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7",
                      dispositions=("2+KK",))
    listing = _make_listing(disposition="2+kk")
    assert apply_filters([listing], spec) == [listing]


def test_min_size_excludes_smaller_and_keeps_unknown():
    spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7", min_size_m2=40)
    big_enough = _make_listing(id="big", size_m2=50)
    too_small = _make_listing(id="small", size_m2=30)
    unknown = _make_listing(id="unknown", size_m2=None)

    result = apply_filters([big_enough, too_small, unknown], spec)

    assert [l.id for l in result] == ["big", "unknown"]


def test_min_land_excludes_smaller_and_keeps_unknown():
    spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7", min_land_m2=200)
    big_enough = _make_listing(id="big", land_m2=300)
    too_small = _make_listing(id="small", land_m2=100)
    unknown = _make_listing(id="unknown", land_m2=None)

    result = apply_filters([big_enough, too_small, unknown], spec)

    assert [l.id for l in result] == ["big", "unknown"]


def test_filters_combine():
    spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7",
                      dispositions=("2+kk",), min_size_m2=40)
    keeper = _make_listing(id="keeper", disposition="2+kk", size_m2=50)
    wrong_disposition = _make_listing(id="wrong-disp", disposition="3+1", size_m2=50)
    too_small = _make_listing(id="too-small", disposition="2+kk", size_m2=30)

    result = apply_filters([keeper, wrong_disposition, too_small], spec)

    assert [l.id for l in result] == ["keeper"]
