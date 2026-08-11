"""Tests for the immutable listing model.

Run: python3 -m pytest tests/test_domain_listing.py -v
"""

import dataclasses

import pytest

from rentczecher.domain.listing import Listing


def _listing(**overrides):
    base = dict(
        id="sreality:1", source="sreality", title="Pronájem bytu 2+kk 55 m²",
        price=21000, location="U Vody, Praha - Holešovice",
        url="https://example.com/1",
    )
    base.update(overrides)
    return Listing.build(**base)


class TestImmutability:
    def test_scraped_fields_cannot_be_assigned(self):
        listing = _listing()
        with pytest.raises(dataclasses.FrozenInstanceError):
            listing.scraped.price = 5

    def test_annotation_fields_cannot_be_assigned(self):
        listing = _listing()
        with pytest.raises(dataclasses.FrozenInstanceError):
            listing.annotations.score = 99

    def test_listing_halves_cannot_be_reassigned(self):
        listing = _listing()
        with pytest.raises(dataclasses.FrozenInstanceError):
            listing.scraped = listing.scraped
        with pytest.raises(dataclasses.FrozenInstanceError):
            listing.annotations = listing.annotations

    def test_passthrough_names_reject_assignment(self):
        # Assigning to a read-only property on a slots dataclass raises
        # TypeError/AttributeError rather than FrozenInstanceError.
        listing = _listing()
        with pytest.raises((TypeError, AttributeError)):
            listing.score = 5
        with pytest.raises((TypeError, AttributeError)):
            listing.price = 5


class TestWithAnnotations:
    def test_returns_new_listing_and_leaves_original_untouched(self):
        original = _listing()
        scored = original.with_annotations(score=73)
        assert scored is not original
        assert scored.score == 73
        assert original.score == 0

    def test_scraped_half_is_shared_not_copied(self):
        original = _listing()
        annotated = original.with_annotations(score=1).with_annotations(nearest_stop="X")
        assert annotated.scraped is original.scraped

    def test_unknown_annotation_is_rejected(self):
        with pytest.raises(TypeError):
            _listing().with_annotations(prize=5)


class TestBuild:
    def test_splits_flat_kwargs_into_both_halves(self):
        listing = _listing(size_m2=55, score=40, cross_source=("remax",))
        assert listing.scraped.size_m2 == 55
        assert listing.annotations.score == 40
        assert listing.annotations.cross_source == ("remax",)

    def test_unknown_field_fails_loudly(self):
        with pytest.raises(TypeError, match="unknown listing fields"):
            _listing(prize=21000)

    def test_passthroughs_read_both_halves(self):
        listing = _listing(size_m2=55, score=40)
        assert listing.price == 21000
        assert listing.size_m2 == 55
        assert listing.score == 40
        assert listing.cross_source == ()


class TestScrapedAt:
    def test_defaults_to_none(self):
        assert _listing().scraped_at is None

    def test_round_trips_a_tz_aware_utc_string(self):
        listing = _listing(scraped_at="2026-08-11T06:00:00+00:00")
        assert listing.scraped_at == "2026-08-11T06:00:00+00:00"
        assert listing.scraped.scraped_at == "2026-08-11T06:00:00+00:00"


class TestEquality:
    def test_same_content_is_equal(self):
        assert _listing() == _listing()

    def test_different_annotations_are_not_equal(self):
        assert _listing() != _listing().with_annotations(score=1)
