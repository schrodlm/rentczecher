"""Tests for cross-source dedup: matching gates, keeper choice, mechanics.

Run: python3 -m pytest tests/test_dedup.py -v
"""

import pytest

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.geo import haversine_m
from rentczecher.domain.location import ParsedPlace, ResolvedPlace
from rentczecher.services import dedup as dedup_module
from rentczecher.services.dedup import cross_source_dedup, promote_fields


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
        back to the gazetteer-resolved place instead of crashing, and a
        shared street name there still carries the pair to a match."""
        shared_place = ParsedPlace(names=("Veletržní", "Praha 7"))
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000,
                           size_m2=50, disposition="2+kk", lat=50.1, lon=None,
                           parsed_place=shared_place)
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                           size_m2=50, disposition="2+kk", lat=50.1001, lon=14.4001,
                           parsed_place=shared_place)
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


class TestPriceGate:
    """Price gate: falsy price never matches; ratio uses max() of the two, strict `>` at 0.10."""

    def test_zero_price_skips_the_price_factor_and_gps_alone_reaches_uncertain(self):
        """A zero price on either side drops the price factor rather than
        vetoing outright; near-identical GPS alone still clears the
        uncertain band, so the pair merges with low confidence."""
        l1 = _make_listing(id="a:1", source="a", price=0, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, lat=50.1001, lon=14.4001)
        assert len(cross_source_dedup([l1, l2])) == 1

        l3 = _make_listing(id="a:2", source="a", price=20000, lat=50.10, lon=14.40)
        l4 = _make_listing(id="b:2", source="b", price=0, lat=50.1001, lon=14.4001)
        assert len(cross_source_dedup([l3, l4])) == 1

    def test_diff_exactly_ten_percent_of_larger_matches(self):
        # 18000 vs 20000: diff/max = 2000/20000 = 0.10 exactly, gate is strict `>` so this passes.
        l1 = _make_listing(id="a:1", source="a", price=20000, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=18000, lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_one_unit_over_price_near_bound_still_merges_on_near_identical_gps(self):
        # 17999 vs 20000: diff/max = 2001/20000 = 0.10005, just over the near-price bound, so the
        # price factor turns barely negative. Near-identical GPS alone still clears the uncertain
        # band, so the two merge with low confidence rather than being vetoed.
        l1 = _make_listing(id="a:1", source="a", price=20000, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=17999, lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_ratio_is_order_independent(self):
        # max() in the denominator means swapping which listing is li/lj doesn't change the outcome.
        a = _make_listing(id="a:1", source="a", price=20000, lat=50.10, lon=14.40)
        b = _make_listing(id="b:1", source="b", price=18000, lat=50.1001, lon=14.4001)
        assert len(cross_source_dedup([a, b])) == len(cross_source_dedup([b, a]))

        c = _make_listing(id="a:2", source="a", price=20000, lat=50.10, lon=14.40)
        d = _make_listing(id="b:2", source="b", price=17999, lat=50.1001, lon=14.4001)
        assert len(cross_source_dedup([c, d])) == len(cross_source_dedup([d, c]))


class TestDispositionFactor:
    """Disposition disagreement outweighs near-identical GPS: same-building units stay separate."""

    def test_both_none_gate_skipped(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, disposition=None,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition=None,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_one_none_gate_skipped(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, disposition=None,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition="3+1",
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_case_insensitive_match(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, disposition="2+KK",
                           size_m2=50, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_disposition_disagreement_outweighs_near_identical_gps(self):
        # GPS (+35) and price (+15) alone would clear the match threshold, but the disposition
        # disagreement (-35) drags the total down to 15, below even the uncertain band.
        l1 = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk",
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition="1+kk",
                           lat=50.100001, lon=14.40)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2


class TestSizeGate:
    """Size gate: 0 is falsy and skips the gate (like the price gate does not); strict `>` at 5."""

    def test_zero_size_on_either_side_skips_gate(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, size_m2=0,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, size_m2=999,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_both_none_skips_gate(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, size_m2=None,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, size_m2=None,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_diff_exactly_five_matches(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, size_m2=50,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, size_m2=55,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_diff_six_still_matches_on_gps_and_price_alone(self):
        # Past the near bound the size factor contributes 0 rather than turning negative outright
        # (diff 6 is still short of the far span), so GPS (+35) and equal price (+15) alone clear
        # the match threshold.
        l1 = _make_listing(id="a:1", source="a", price=20000, size_m2=50,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, size_m2=56,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1


class TestGpsGate:
    """GPS factor: <=100m is the ceiling (immediate accept on GPS alone with any positive
    corroboration), >=1500m is the negative ceiling, and the (100, 1500) band is graded by
    distance. Deltas below are derived with haversine_m and asserted precisely so the fixtures
    prove the boundary they claim."""

    BASE_LAT = 50.1
    BASE_LON = 14.4

    def test_any_coord_none_falls_back_to_the_resolved_place_and_a_shared_street_still_matches(self):
        # Half-set GPS on one side falls back to the gazetteer's centroid for the resolved place,
        # so the other listing's own GPS must be near THAT centroid (not just near the half-set
        # listing's dropped coordinate) for the fallback to read as a real match.
        shared_place = ParsedPlace(names=("Veletržní", "Praha 7"))
        l1 = _make_listing(id="a:1", source="a", price=20000, lat=None, lon=14.4270,
                           parsed_place=shared_place)
        l2 = _make_listing(id="b:1", source="b", price=20000, lat=50.1015, lon=14.4298,
                           parsed_place=shared_place)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

        l3 = _make_listing(id="a:2", source="a", price=20000, lat=50.1015, lon=None,
                           parsed_place=shared_place)
        l4 = _make_listing(id="b:2", source="b", price=20000, lat=50.1015, lon=14.4298,
                           parsed_place=shared_place)
        result2 = cross_source_dedup([l3, l4])
        assert len(result2) == 1

    def test_101m_is_graded_not_ceiling_but_equal_price_still_clears_match(self):
        dlat = 0.0009038182139455841
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist == 101

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON)
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_exactly_100m_is_the_ceiling(self):
        dlat = 0.0008948249978892875
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist == 100

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON)
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_1499m_is_graded_and_stays_no_match_with_no_other_evidence(self):
        dlat = 0.013476334264691305
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist == 1499

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON)
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_exactly_1500m_is_the_negative_ceiling(self):
        dlat = 0.013485327480754705
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist == 1500

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON)
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_1000m_graded_gps_merges_with_low_confidence_on_a_shared_street_name(self):
        dlat = 0.008988719451156868
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist == 1000

        shared_place = ParsedPlace(names=("Veletržní", "Praha 7"))
        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON, parsed_place=shared_place)
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON, parsed_place=shared_place)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1


class TestSharedNameFactorWithNoGps:
    """With neither listing carrying GPS, a shared gazetteer-resolved name is the only path
    to the evidence floor: the free-text `.location` string itself carries no weight."""

    def test_no_parsed_place_names_on_either_side_never_matches(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, location="")
        l2 = _make_listing(id="b:1", source="b", price=20000, location="Praha 7")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_shared_street_name_alone_clears_the_evidence_floor_and_matches(self):
        shared_place = ParsedPlace(names=("Veletržní",))
        l1 = _make_listing(id="a:1", source="a", price=20000, parsed_place=shared_place)
        l2 = _make_listing(id="b:1", source="b", price=20000, parsed_place=shared_place)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_different_street_names_do_not_match(self):
        # Both sides carry a street-tier name and share none, so the streets-disagree
        # penalty (-25) applies on top of - not instead of - the price factor.
        l1 = _make_listing(id="a:1", source="a", price=20000,
                           parsed_place=ParsedPlace(names=("Veletržní",)))
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           parsed_place=ParsedPlace(names=("Korunní",)))
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2


class TestKeeperChoice:
    """Completeness score: lat, charges, land_m2, size_m2 (is not None) + image_url (bool)."""

    def test_exact_tie_keeps_first_in_input_order(self):
        l1 = _make_listing(id="s:1", source="s", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1
        assert result[0].id == "s:1"

    def test_empty_string_image_scores_same_as_none(self):
        # image_url uses bool() (:94) rather than the `is not None` used for the other
        # four completeness fields, so "" and None are indistinguishable here.
        l1 = _make_listing(id="s:1", source="s", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.10, lon=14.40, image_url="")
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.1001, lon=14.4001, image_url=None)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1
        assert result[0].id == "s:1"

    def test_one_extra_field_flips_keeper_to_richer_listing(self):
        l1 = _make_listing(id="s:1", source="s", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, disposition="2+kk",
                           size_m2=50, lat=50.1001, lon=14.4001, charges=1500)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1
        assert result[0].id == "b:1"


class TestOrderingMechanics:
    """Survivors preserve original input order; a keeper stays at its own position."""

    def test_survivor_order_matches_input_order(self):
        x = _make_listing(id="x:1", source="x", price=20000, disposition="2+kk",
                          size_m2=50, lat=50.10, lon=14.40)
        y = _make_listing(id="y:1", source="y", price=20000, disposition="2+kk",
                          size_m2=50, lat=50.1001, lon=14.4001)
        z = _make_listing(id="z:1", source="z", price=99999, location="Nowhere special zzz")

        result = cross_source_dedup([x, y, z])
        assert [listing.id for listing in result] == ["x:1", "z:1"]


class TestNoTransitiveGrouping:
    """The dedup loop does strict pairwise matching with no transitive/graph-closure grouping:
    a merge only happens when the SAME listing is directly compared to both others before either
    is removed. Whether that happens is entirely a function of input order."""

    def test_three_mutually_non_matching_survive_all(self):
        a = _make_listing(id="a:1", source="a", price=15000, location="Alpha Nowhere")
        b = _make_listing(id="b:1", source="b", price=25000, location="Beta Elsewhere")
        c = _make_listing(id="c:1", source="c", price=99999, location="Gamma Faraway")
        result = cross_source_dedup([a, b, c])
        assert len(result) == 3

    def test_shared_middle_compared_first_merges_all_three(self):
        # A-B diff ~6.98%, B-C diff ~6.52%, A-C diff ~13.04% (>10%, so A and C alone never match).
        # With B listed first, B is the outer-loop `i` and gets directly compared to both A and C
        # before either is removed -- two direct pairwise matches sharing B, not graph closure.
        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk",
                          size_m2=50, lat=50.10, lon=14.40)
        b = _make_listing(id="b:1", source="b", price=21500, disposition="2+kk",
                          size_m2=50, lat=50.1005, lon=14.4005)
        c = _make_listing(id="c:1", source="c", price=23000, disposition="2+kk",
                          size_m2=50, lat=50.1010, lon=14.4010)

        result = cross_source_dedup([b, a, c])
        assert len(result) == 1
        assert result[0].id == "b:1"
        assert set(result[0].cross_source) == {"a", "c"}

    def test_direct_ac_match_merges_all_three_regardless_of_order(self):
        # Same trio as above, ordered [A, B, C]. A-C alone is 13.04% apart in price, but GPS,
        # disposition and size all agree, so A~C now scores a direct match on its own -- this
        # is a straight pairwise match, not graph closure through B. A~B matches first (A richer,
        # so A keeps and B is removed); A is then compared to C directly and matches too.
        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk", size_m2=50,
                          lat=50.10, lon=14.40, charges=1000, land_m2=10, image_url="http://x")
        b = _make_listing(id="b:1", source="b", price=21500, disposition="2+kk",
                          size_m2=50, lat=50.1005, lon=14.4005)
        c = _make_listing(id="c:1", source="c", price=23000, disposition="2+kk",
                          size_m2=50, lat=50.1010, lon=14.4010)

        result = cross_source_dedup([a, b, c])
        assert len(result) == 1
        assert result[0].id == "a:1"
        assert set(result[0].cross_source) == {"b", "c"}

    def test_direct_ac_match_merges_all_three_in_reversed_order_and_carries_the_middle_source(self):
        # Same trio, order reversed to [C, B, A]. C~B matches first (tied completeness, so C -- the
        # earlier index -- keeps B, recorded as remove_to_keeper[B]=C). C is then compared to A
        # directly: A is richer, so this time C itself is removed in A's favor
        # (remove_to_keeper[C]=A). C's absorbed source (B) re-parents onto A when C is displaced,
        # so the final survivor A carries both B and C even though C never survives itself.
        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk", size_m2=50,
                          lat=50.10, lon=14.40, charges=1000, land_m2=10, image_url="http://x")
        b = _make_listing(id="b:1", source="b", price=21500, disposition="2+kk",
                          size_m2=50, lat=50.1005, lon=14.4005)
        c = _make_listing(id="c:1", source="c", price=23000, disposition="2+kk",
                          size_m2=50, lat=50.1010, lon=14.4010)

        result = cross_source_dedup([c, b, a])
        assert len(result) == 1
        assert result[0].id == "a:1"
        assert set(result[0].cross_source) == {"b", "c"}


class TestCrossSourceAccumulation:
    """A keeper absorbing multiple listings accumulates all their sources, in absorption order."""

    def test_keeper_accumulates_both_sources_in_order(self):
        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk", size_m2=50,
                          lat=50.10, lon=14.40, charges=1, land_m2=1, image_url="x")
        b = _make_listing(id="b:1", source="b", price=20000, disposition="2+kk",
                          size_m2=50, lat=50.1001, lon=14.4001)
        c = _make_listing(id="c:1", source="c", price=20000, disposition="2+kk",
                          size_m2=50, lat=50.1002, lon=14.4002)

        result = cross_source_dedup([a, b, c])
        assert len(result) == 1
        assert result[0].id == "a:1"
        assert result[0].cross_source == ("b", "c")


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


class TestScoredMatcherInvariants:
    """The scored matcher scores every pair on the original scraped
    listings, never on an already-merged keeper, and locate() is called
    once per listing regardless of how many pairs are scored."""

    def test_locate_call_count_is_linear_in_listing_count(self, gazetteer, monkeypatch):
        calls = []
        real_locate = dedup_module.locate

        def counting_locate(listing, gaz):
            calls.append(listing.id)
            return real_locate(listing, gaz)

        monkeypatch.setattr(dedup_module, "locate", counting_locate)

        listings = [
            _make_listing(id="a:1", source="a", price=20000, size_m2=50, disposition="2+kk",
                         lat=50.10, lon=14.40),
            _make_listing(id="b:1", source="b", price=20000, size_m2=50, disposition="2+kk",
                         lat=50.1001, lon=14.4001),
            _make_listing(id="c:1", source="c", price=25000, size_m2=60, disposition="3+kk",
                         lat=49.0, lon=13.0),
            _make_listing(id="d:1", source="d", price=25000, size_m2=60, disposition="3+kk",
                         lat=49.0001, lon=13.0001),
        ]
        cross_source_dedup(listings, gazetteer)
        assert len(calls) <= 4

    def test_survivor_is_scored_against_the_original_listing_not_the_merged_keeper(self, gazetteer):
        # A and B merge on near-identical GPS, matching price/size/disposition.
        # C is far from both A and B (~18km) with a mismatched disposition and
        # price, so raw A~C and raw B~C both score no_match on their own -
        # nothing about A absorbing B's source changes what C is compared
        # against, so C must survive unmerged.
        a = _make_listing(id="a:1", source="a", price=20000, size_m2=50, disposition="2+kk",
                          lat=50.10, lon=14.40)
        b = _make_listing(id="b:1", source="b", price=20000, size_m2=50, disposition="2+kk",
                          lat=50.1001, lon=14.4001)
        c = _make_listing(id="c:1", source="c", price=40000, size_m2=20, disposition="3+kk",
                          lat=50.20, lon=14.60)

        result = cross_source_dedup([a, b, c], gazetteer)

        by_id = {listing.id: listing for listing in result}
        assert "c:1" in by_id
        assert by_id["c:1"].cross_source == ()
        assert len(result) == 2

    def test_evidence_floor_rejects_a_naive_forty_with_no_gps_or_shared_name(self, gazetteer):
        # Price (+15), size (+10) and disposition (+15) alone sum to exactly
        # the match threshold, but neither listing carries GPS (portal or
        # gazetteer-resolved) nor any parsed_place name, so the evidence
        # floor (GPS or shared-name evidence) is never met and the pair must
        # not merge despite the naive total.
        a = _make_listing(id="a:1", source="a", price=20000, size_m2=50, disposition="2+kk")
        b = _make_listing(id="b:1", source="b", price=20000, size_m2=50, disposition="2+kk")

        result = cross_source_dedup([a, b], gazetteer)
        assert len(result) == 2


class TestVeletrzniShapedMatch:
    """A shared street name with mid-band GPS clears the match threshold even
    when the portals label the street with different municipality parts -
    no single disagreeing label can veto the pair."""

    def test_shared_street_name_with_midband_gps_matches(self, gazetteer):
        lat_a, lon_a = 50.1005, 14.4270
        lat_b, lon_b = 50.1059054054054, 14.4270
        dist = haversine_m(lat_a, lon_a, lat_b, lon_b)
        assert 400 < dist < 1500, "must land in the GPS mid-band, not an immediate accept/reject"

        a = _make_listing(id="a:1", source="a", price=20000, size_m2=50, disposition="2+kk",
                          lat=lat_a, lon=lon_a, location="Veletržní 1<>2",
                          parsed_place=ParsedPlace(names=("Veletržní", "Praha")))
        b = _make_listing(id="b:1", source="b", price=20000, size_m2=50, disposition="2+kk",
                          lat=lat_b, lon=lon_b, location="Praha 7 - Bubeneč",
                          parsed_place=ParsedPlace(names=("Veletržní", "Bubeneč")))

        result = cross_source_dedup([a, b], gazetteer)
        assert len(result) == 1


class TestGeocellBoundaries:
    """Geocells block candidate lookups; they never decide a match - a
    close pair straddling a cell edge still merges."""

    def test_pair_straddling_a_cell_edge_merges(self):
        from rentczecher.domain.geo import CELL_LAT_DEG
        edge = 4640 * CELL_LAT_DEG
        shared = ParsedPlace(names=("U Vody", "Praha"))
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000,
                           size_m2=55, disposition="2+kk",
                           lat=edge - 0.0005, lon=14.44, parsed_place=shared)
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                           size_m2=55, disposition="2+kk",
                           lat=edge + 0.0005, lon=14.44, parsed_place=shared)
        assert len(cross_source_dedup([l1, l2])) == 1


class TestStreetsDisagreeVetoesASharedPart:
    """Two listings that each name a street, agreeing on none, do not merge even
    when they share a coarser name (the same municipality part) and everything
    else - close centroids, equal price, disposition, and size - would otherwise
    read as a match: different streets are evidence of different properties, and
    a coarser shared name cannot mask that."""

    def test_adjacent_streets_with_everything_else_identical_merge_uncertain(self):
        """Near-identical GPS plus agreeing price, size, and disposition
        outweigh a street-name disagreement - two listings meters apart and
        identical everywhere else are far likelier one property with a
        divergent street label than two coincidentally identical neighbors.
        The pair merges in the low-confidence band."""
        l1 = _make_listing(id="sreality:1", source="sreality", price=20000,
                           size_m2=55, disposition="2+kk", lat=50.1000, lon=14.44,
                           parsed_place=ParsedPlace(names=("U Vody", "Praha", "Holešovice")))
        l2 = _make_listing(id="bezrealitky:1", source="bezrealitky", price=20000,
                           size_m2=55, disposition="2+kk", lat=50.1013, lon=14.44,
                           parsed_place=ParsedPlace(names=("Veverkova", "Praha", "Holešovice")))
        assert len(cross_source_dedup([l1, l2])) == 1

    def test_shared_municipality_part_does_not_paper_over_disagreeing_streets(self, gazetteer):
        lat_a, lon_a = 50.1035, 14.4405
        lat_b, lon_b = 50.1095, 14.4405
        dist = haversine_m(lat_a, lon_a, lat_b, lon_b)
        assert 100 < dist < 1500, "close but not an immediate GPS-ceiling accept on its own"

        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk", size_m2=50,
                          lat=lat_a, lon=lon_a,
                          parsed_place=ParsedPlace(names=("U Vody", "Praha", "Holešovice")))
        b = _make_listing(id="b:1", source="b", price=20000, disposition="2+kk", size_m2=50,
                          lat=lat_b, lon=lon_b,
                          parsed_place=ParsedPlace(names=("Veverkova", "Praha", "Holešovice")))

        result = cross_source_dedup([a, b], gazetteer)
        assert len(result) == 2

    def test_shared_part_name_that_is_a_street_elsewhere_stays_a_part(self, gazetteer):
        """A shared neighborhood name some other municipality uses as a
        street name ('Bubeneč' is a street in Lenešice) is read within the
        listings' own municipality: it earns part-level credit only, and it
        does not shield the disagreeing actual streets from their penalty."""
        lat_a, lon_a = 50.0983, 14.4194
        lat_b, lon_b = 50.1027, 14.4249
        dist = haversine_m(lat_a, lon_a, lat_b, lon_b)
        assert 100 < dist < 1500, "close but not an immediate GPS-ceiling accept on its own"

        a = _make_listing(id="sreality:1", source="sreality", price=22000,
                          size_m2=35, disposition="1+kk", lat=lat_a, lon=lon_a,
                          parsed_place=ParsedPlace(names=("Korunovační", "Praha", "Bubeneč")))
        b = _make_listing(id="bezrealitky:1", source="bezrealitky", price=22500,
                          size_m2=37, disposition="1+kk", lat=lat_b, lon=lon_b,
                          parsed_place=ParsedPlace(names=("U studánky", "Praha", "Bubeneč")))

        result = cross_source_dedup([a, b], gazetteer)
        assert len(result) == 2


class TestPromoteFields:
    """promote_fields is a pure function with no pipeline caller yet - tests
    are its only consumer. Kept's value wins wherever present; absorbed only
    fills a gap kept left; location (and lat/lon with it) follows whichever
    side's place evidence sits at the more specific tier."""

    def test_kept_value_wins_over_a_present_absorbed_value(self):
        kept = _make_listing(title="Kept title", size_m2=50, disposition="2+kk", land_m2=10)
        absorbed = _make_listing(title="Absorbed title", size_m2=48, disposition="1+kk", land_m2=20)

        canonical, _ = promote_fields(kept, absorbed)

        assert canonical["title"] == "Kept title"
        assert canonical["size_m2"] == 50
        assert canonical["disposition"] == "2+kk"
        assert canonical["land_m2"] == 10

    def test_absorbed_fills_every_gap_kept_leaves(self):
        kept = _make_listing(title="", size_m2=None, disposition=None, land_m2=None, lat=None, lon=None)
        absorbed = _make_listing(title="Absorbed title", size_m2=48, disposition="1+kk", land_m2=20,
                                  lat=50.1, lon=14.4)

        canonical, differences = promote_fields(kept, absorbed)

        assert canonical["title"] == "Absorbed title"
        assert canonical["size_m2"] == 48
        assert canonical["disposition"] == "1+kk"
        assert canonical["land_m2"] == 20
        assert canonical["lat"] == 50.1
        assert canonical["lon"] == 14.4
        assert differences == {}

    def test_location_prefers_the_more_specific_tier_regardless_of_which_side_kept_is(self):
        kept = _make_listing(location="Praha 7", lat=None, lon=None,
                              place=ResolvedPlace(name="Praha 7", muni_name="Praha", okres_name=None,
                                                   tier="city_district", lat=50.09, lon=14.42))
        absorbed = _make_listing(location="Veletržní 1", lat=None, lon=None,
                                  place=ResolvedPlace(name="Veletržní", muni_name="Praha", okres_name=None,
                                                       tier="street", lat=50.1005, lon=14.4270))

        canonical, _ = promote_fields(kept, absorbed)

        assert canonical["location"] == "Veletržní 1"
        assert canonical["lat"] == 50.1005
        assert canonical["lon"] == 14.4270

    def test_location_keeps_kept_when_kept_tier_is_already_the_more_specific(self):
        kept = _make_listing(location="Veletržní 1", lat=50.1005, lon=14.4270)
        absorbed = _make_listing(location="Praha 7", lat=None, lon=None,
                                  place=ResolvedPlace(name="Praha 7", muni_name="Praha", okres_name=None,
                                                       tier="city_district", lat=50.09, lon=14.42))

        canonical, _ = promote_fields(kept, absorbed)

        assert canonical["location"] == "Veletržní 1"
        assert canonical["lat"] == 50.1005
        assert canonical["lon"] == 14.4270

    def test_differences_shape_matches_the_dedup_records_json_shape(self):
        kept = _make_listing(disposition="2+kk", size_m2=50)
        absorbed = _make_listing(disposition="1+kk", size_m2=48)

        _, differences = promote_fields(kept, absorbed)

        assert differences["disposition"] == {"canonical": "2+kk", "listing": "1+kk"}
        assert differences["size_m2"] == {"canonical": 50, "listing": 48}

    def test_no_differences_when_every_field_is_identical(self):
        kept = _make_listing(title="Same", location="Praha 7", size_m2=50, disposition="2+kk",
                              land_m2=10, lat=50.1, lon=14.4)
        absorbed = _make_listing(title="Same", location="Praha 7", size_m2=50, disposition="2+kk",
                                  land_m2=10, lat=50.1, lon=14.4)

        _, differences = promote_fields(kept, absorbed)

        assert differences == {}

    def test_disposition_casing_disagreement_is_not_a_genuine_difference(self):
        kept = _make_listing(disposition="2+KK")
        absorbed = _make_listing(disposition="2+kk")

        _, differences = promote_fields(kept, absorbed)

        assert differences == {}
