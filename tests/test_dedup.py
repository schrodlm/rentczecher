"""Tests for cross-source dedup: matching gates, keeper choice, mechanics.

Run: python3 -m pytest tests/test_dedup.py -v
"""

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.geo import haversine_m
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


class TestPriceGate:
    """Price gate: falsy price never matches; ratio uses max() of the two, strict `>` at 0.10."""

    def test_zero_price_on_either_side_never_matches(self):
        l1 = _make_listing(id="a:1", source="a", price=0, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, lat=50.1001, lon=14.4001)
        assert cross_source_dedup([l1, l2]) == [l1, l2]

        l3 = _make_listing(id="a:2", source="a", price=20000, lat=50.10, lon=14.40)
        l4 = _make_listing(id="b:2", source="b", price=0, lat=50.1001, lon=14.4001)
        assert cross_source_dedup([l3, l4]) == [l3, l4]

    def test_diff_exactly_ten_percent_of_larger_matches(self):
        # 18000 vs 20000: diff/max = 2000/20000 = 0.10 exactly, gate is strict `>` so this passes.
        l1 = _make_listing(id="a:1", source="a", price=20000, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=18000, lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_one_unit_over_boundary_does_not_match(self):
        # 17999 vs 20000: diff/max = 2001/20000 = 0.10005, just over the strict 0.10 cutoff.
        l1 = _make_listing(id="a:1", source="a", price=20000, lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=17999, lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_ratio_is_order_independent(self):
        # max() in the denominator means swapping which listing is li/lj doesn't change the outcome.
        a = _make_listing(id="a:1", source="a", price=20000, lat=50.10, lon=14.40)
        b = _make_listing(id="b:1", source="b", price=18000, lat=50.1001, lon=14.4001)
        assert len(cross_source_dedup([a, b])) == len(cross_source_dedup([b, a]))

        c = _make_listing(id="a:2", source="a", price=20000, lat=50.10, lon=14.40)
        d = _make_listing(id="b:2", source="b", price=17999, lat=50.1001, lon=14.4001)
        assert len(cross_source_dedup([c, d])) == len(cross_source_dedup([d, c]))


class TestDispositionGate:
    """Disposition gate runs before the GPS check, so a mismatch vetoes even near-identical GPS."""

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

    def test_mismatch_vetoes_despite_near_identical_gps(self):
        # Disposition gate (before GPS check) rejects here even though the two
        # points are ~0.1m apart, which would otherwise be an immediate GPS accept.
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

    def test_diff_six_does_not_match(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, size_m2=50,
                           lat=50.10, lon=14.40)
        l2 = _make_listing(id="b:1", source="b", price=20000, size_m2=56,
                           lat=50.1001, lon=14.4001)
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2


class TestGpsGate:
    """GPS gate: all four coords required; <200m immediate accept, >1000m immediate reject,
    the [200, 1000] band falls through to location-token overlap. Deltas below are derived with
    haversine_m and asserted precisely so the fixtures prove the boundary they claim."""

    BASE_LAT = 50.1
    BASE_LON = 14.4

    def test_any_coord_none_falls_through_to_location_overlap(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, lat=None, lon=14.40,
                           location="Praha 7 Holesovice")
        l2 = _make_listing(id="b:1", source="b", price=20000, lat=50.9999, lon=14.4001,
                           location="Praha 7 Holesovice")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

        l3 = _make_listing(id="a:2", source="a", price=20000, lat=50.10, lon=None,
                           location="Praha 7 Holesovice")
        l4 = _make_listing(id="b:2", source="b", price=20000, lat=50.9999, lon=14.4001,
                           location="Praha 7 Holesovice")
        result2 = cross_source_dedup([l3, l4])
        assert len(result2) == 1

    def test_exactly_200m_is_not_immediate_accept(self):
        dlat = 0.0017941466038102762
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist >= 200

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON, location="Zeta Alpha Nowhere")
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON,
                           location="Beta Gamma Elsewhere")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_just_under_200m_is_immediate_accept(self):
        dlat = 0.0017851533877468737
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist < 200

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON, location="Zeta Alpha Nowhere")
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON,
                           location="Beta Gamma Elsewhere")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_just_over_1000m_rejects_despite_overlapping_locations(self):
        dlat = 0.008997712667220272
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist > 1000

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON, location="Praha 7 Holesovice")
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON,
                           location="Praha 7 Holesovice")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_1000m_falls_through_and_matches_via_token_overlap(self):
        dlat = 0.008988719451156868
        dist = haversine_m(self.BASE_LAT, self.BASE_LON, self.BASE_LAT + dlat, self.BASE_LON)
        assert dist <= 1000

        l1 = _make_listing(id="a:1", source="a", price=20000,
                           lat=self.BASE_LAT, lon=self.BASE_LON, location="Praha 7 Holesovice")
        l2 = _make_listing(id="b:1", source="b", price=20000,
                           lat=self.BASE_LAT + dlat, lon=self.BASE_LON,
                           location="Praha 7 Holesovice")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1


class TestLocationTokenOverlap:
    """Location-token overlap, driven with no GPS on either listing."""

    def test_empty_location_either_side_no_match(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, location="")
        l2 = _make_listing(id="b:1", source="b", price=20000, location="Praha 7")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_locations_normalize_equal(self):
        # ASCII spellings so normalization (lower, strip punctuation/dashes) is what equalizes
        # them, not a diacritics coincidence.
        l1 = _make_listing(id="a:1", source="a", price=20000, location="Praha, Holesovice")
        l2 = _make_listing(id="b:1", source="b", price=20000, location="praha - holesovice")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_shared_token_length_three_counts(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, location="xyz abc")
        l2 = _make_listing(id="b:1", source="b", price=20000, location="qqq abc")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 1

    def test_shared_token_length_two_does_not_count(self):
        l1 = _make_listing(id="a:1", source="a", price=20000, location="xyz ab")
        l2 = _make_listing(id="b:1", source="b", price=20000, location="qqq ab")
        result = cross_source_dedup([l1, l2])
        assert len(result) == 2

    def test_skip_words_only_location_no_match(self):
        # "praha" is a SKIP_WORDS entry, so it never counts as a shared token
        # even when both sides are identical.
        l1 = _make_listing(id="a:1", source="a", price=20000, location="Praha")
        l2 = _make_listing(id="b:1", source="b", price=20000, location="Praha")
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

    def test_consumed_middle_never_reaches_third_listing(self):
        # Same trio as above, but ordered [A, B, C]. A~B matches (A richer, so A keeps and B is
        # removed). B~C would also match in isolation, but B is skipped as soon as it becomes the
        # outer-loop `i` because it is already in remove_to_keeper (:77) -- so B is never compared
        # to C, and C survives unmerged even though a match exists on paper.
        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk", size_m2=50,
                          lat=50.10, lon=14.40, charges=1000, land_m2=10, image_url="http://x")
        b = _make_listing(id="b:1", source="b", price=21500, disposition="2+kk",
                          size_m2=50, lat=50.1005, lon=14.4005)
        c = _make_listing(id="c:1", source="c", price=23000, disposition="2+kk",
                          size_m2=50, lat=50.1010, lon=14.4010)

        result = cross_source_dedup([a, b, c])
        assert len(result) == 2
        by_id = {listing.id: listing for listing in result}
        assert set(by_id["a:1"].cross_source) == {"b"}
        assert by_id["c:1"].cross_source == ()

    def test_reversed_order_changes_which_end_survives(self):
        # Same trio, order reversed to [C, B, A]. Now C is compared to B first: B and C tie on
        # completeness (neither has charges/land/image), and the gate uses `i_score >= j_score`,
        # so C (the earlier index) keeps B. A is then compared to C and fails (A~C is false), so
        # A survives alone. Input order decides which end of the chain survives.
        a = _make_listing(id="a:1", source="a", price=20000, disposition="2+kk", size_m2=50,
                          lat=50.10, lon=14.40, charges=1000, land_m2=10, image_url="http://x")
        b = _make_listing(id="b:1", source="b", price=21500, disposition="2+kk",
                          size_m2=50, lat=50.1005, lon=14.4005)
        c = _make_listing(id="c:1", source="c", price=23000, disposition="2+kk",
                          size_m2=50, lat=50.1010, lon=14.4010)

        result = cross_source_dedup([c, b, a])
        assert len(result) == 2
        by_id = {listing.id: listing for listing in result}
        assert set(by_id["c:1"].cross_source) == {"b"}
        assert by_id["a:1"].cross_source == ()


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
