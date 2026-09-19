"""Tests for classifying a run's survivors into new, price-dropped, and
disappeared.

Run: python3 -m pytest tests/test_diff.py -v
"""

from rentczecher.domain.listing import DisappearedListing, Listing
from rentczecher.services.diff import classify


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="sreality:1", source="sreality", title="Pronájem bytu 2+kk 50 m²",
        price=20000, location="Veletržní, Praha 7", url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def test_every_unseen_listing_is_reported_new_and_nothing_else():
    listings = [_make_listing(id="a"), _make_listing(id="b")]

    diff = classify(listings, seen_ids=set(), latest_prices={}, disappeared=[])

    assert [l.id for l in diff.new] == ["a", "b"]
    assert diff.price_drops == []
    assert diff.disappeared == []


def test_a_lower_price_than_last_seen_is_reported_as_a_drop_carrying_the_old_price():
    listing = _make_listing(id="a", price=16000)

    diff = classify([listing], seen_ids={"a"}, latest_prices={"a": 18000}, disappeared=[])

    assert diff.new == []
    assert len(diff.price_drops) == 1
    dropped = diff.price_drops[0]
    assert dropped.id == "a"
    assert dropped.price == 16000
    assert dropped.price_drop_from == 18000


def test_a_listing_new_this_run_is_never_also_reported_as_a_drop():
    listing = _make_listing(id="a", price=16000)

    diff = classify([listing], seen_ids=set(), latest_prices={"a": 18000}, disappeared=[])

    assert [l.id for l in diff.new] == ["a"]
    assert diff.price_drops == []


def test_a_listing_with_no_recorded_price_is_never_reported_as_a_drop():
    listing = _make_listing(id="a", price=16000)

    diff = classify([listing], seen_ids={"a"}, latest_prices={}, disappeared=[])

    assert diff.new == []
    assert diff.price_drops == []


def test_disappeared_records_pass_through_unchanged():
    gone = DisappearedListing(
        id="sreality:gone", source="sreality", url="https://example.com/gone",
        first_seen_at="2026-09-01T00:00:00+00:00", miss_count=3,
        title="Pronájem bytu 1+kk 30 m²", location="Tusarova, Praha 7", price=15000,
    )

    diff = classify([], seen_ids=set(), latest_prices={}, disappeared=[gone])

    assert diff.disappeared == [gone]
