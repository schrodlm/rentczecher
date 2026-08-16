"""Tests for cross-source dedup: matching gates, keeper choice, mechanics.

Run: python3 -m pytest tests/test_dedup.py -v
"""

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.services.dedup import cross_source_dedup


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test:1", source="test", title="Test", price=20000,
        location="Praha 7 - Holešovice", url="https://example.com",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


class TestDedup:
    def test_same_flat_different_sources_deduped(self):
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000,
                           size_m2=50, disposition="2+kk", lat=50.1, lon=14.4)
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                           size_m2=50, disposition="2+kk", lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1, "Same flat should be deduped"
        assert len(result[0].cross_source) == 1

    def test_listing_with_lat_but_no_lon_does_not_crash(self):
        """GPS matching requires all four coordinates; a half-set pair falls
        through to location matching instead of crashing."""
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000,
                           size_m2=50, disposition="2+kk", lat=50.1, lon=None)
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                           size_m2=50, disposition="2+kk", lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_different_price_not_deduped(self):
        l1 = _make_listing(id="sreality:1", source="sreality", price=15000,
                           lat=50.1, lon=14.4)
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=25000,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2, "Different prices should not dedup"

    def test_same_source_not_deduped(self):
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000)
        l2 = _make_listing(id="sreality:2", source="sreality", price=20000)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2, "Same source should not dedup"

    def test_gps_far_apart_not_deduped(self):
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000,
                           lat=50.1, lon=14.4)
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                           lat=50.2, lon=14.5)  # ~12km away
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2, "GPS far apart should not dedup"

    def test_empty_list(self):
        assert cross_source_dedup([]) == []

    def test_single_listing(self):
        l = _make_listing()
        assert cross_source_dedup([l]) == [l]


class TestDedupCrossSourceCorrectness:
    """After dedup, no listing should have its OWN source in cross_source."""

    def test_own_source_never_in_cross_source(self):
        listings = [
            _make_listing(id="sreality:1", source="sreality", price=20000,
                          size_m2=50, disposition="2+kk", lat=50.1, lon=14.4),
            _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                          size_m2=50, disposition="2+kk", lat=50.1001, lon=14.4001),
            _make_listing(id="remax:1", source="remax", price=20000,
                          size_m2=50, disposition="2+kk", lat=50.1002, lon=14.4002),
        ]

        result = cross_source_dedup(listings)

        for listing in result:
            assert listing.source not in listing.cross_source, (
                f"Listing {listing.id} (source={listing.source}) has its own "
                f"source in cross_source: {listing.cross_source}"
            )

    def test_own_source_excluded_two_pairs(self):
        """Two separate dedup groups -- verify for each keeper."""
        # Group A: close GPS, same price
        a1 = _make_listing(id="sreality:a", source="sreality", price=18000,
                           size_m2=40, disposition="1+kk", lat=50.0, lon=14.0)
        a2 = _make_listing(id="bezrealitky:a", source="bezrealitky", price=18000,
                           size_m2=40, disposition="1+kk", lat=50.0001, lon=14.0001)

        # Group B: different area
        b1 = _make_listing(id="sreality:b", source="sreality", price=25000,
                           size_m2=60, disposition="3+kk", lat=49.0, lon=13.0)
        b2 = _make_listing(id="remax:b", source="remax", price=25000,
                           size_m2=60, disposition="3+kk", lat=49.0001, lon=13.0001)

        result = cross_source_dedup([a1, a2, b1, b2])

        for listing in result:
            assert listing.source not in listing.cross_source


class TestDedupThreeSources:
    """3 listings (sreality, bezrealitky, remax) for the same flat merge into 1."""

    def test_three_sources_merge_into_one(self):
        listings = [
            _make_listing(id="sreality:100", source="sreality", price=22000,
                          size_m2=55, disposition="2+kk", lat=50.1, lon=14.4,
                          location="Praha 7"),
            _make_listing(id="bezrealitky:200", source="bezrealitky", price=22000,
                          size_m2=55, disposition="2+kk", lat=50.1001, lon=14.4001,
                          location="Praha 7"),
            _make_listing(id="remax:300", source="remax", price=22000,
                          size_m2=55, disposition="2+kk", lat=50.1002, lon=14.4002,
                          location="Praha 7"),
        ]

        result = cross_source_dedup(listings)
        assert len(result) == 1, f"Expected 1 merged listing, got {len(result)}"

    def test_three_sources_cross_source_has_two_entries(self):
        listings = [
            _make_listing(id="sreality:100", source="sreality", price=22000,
                          size_m2=55, disposition="2+kk", lat=50.1, lon=14.4,
                          location="Praha 7"),
            _make_listing(id="bezrealitky:200", source="bezrealitky", price=22000,
                          size_m2=55, disposition="2+kk", lat=50.1001, lon=14.4001,
                          location="Praha 7"),
            _make_listing(id="remax:300", source="remax", price=22000,
                          size_m2=55, disposition="2+kk", lat=50.1002, lon=14.4002,
                          location="Praha 7"),
        ]

        result = cross_source_dedup(listings)
        keeper = result[0]

        # cross_source should contain exactly the two OTHER sources
        expected_others = {"sreality", "bezrealitky", "remax"} - {keeper.source}
        assert set(keeper.cross_source) == expected_others, (
            f"Keeper source={keeper.source}, cross_source={keeper.cross_source}, "
            f"expected others={expected_others}"
        )
