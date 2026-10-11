"""Tests for the price records and collapsing observations into changes.

Run: python3 -m pytest tests/test_domain_price.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.domain.price import PriceChange, PriceObservation, price_changes


def test_is_immutable():
    obs = PriceObservation(listing_id="sreality:1", price=100,
                           observed_at="2026-08-11T06:00:00+00:00")
    with pytest.raises(dataclasses.FrozenInstanceError):
        obs.price = 200  # type: ignore[misc]


def test_charges_and_run_id_are_optional():
    obs = PriceObservation(listing_id="sreality:1", price=100,
                           observed_at="2026-08-11T06:00:00+00:00")
    assert obs.charges is None
    assert obs.observed_in_run_id is None


def test_carries_a_tz_aware_observed_at():
    obs = PriceObservation(listing_id="sreality:1", price=100,
                           observed_at="2026-08-11T06:00:00+00:00")
    assert obs.observed_at == "2026-08-11T06:00:00+00:00"


def _seen(day: int, price: int, charges: int | None = None) -> PriceObservation:
    return PriceObservation(listing_id="sreality:1", price=price, charges=charges,
                            observed_at=f"2026-10-{day:02d}T06:00:00+00:00")


class TestPriceChanges:
    def test_collapses_repeat_scans_into_one_held_price(self):
        changes = price_changes([_seen(1, 20000), _seen(2, 20000), _seen(3, 20000)])
        assert changes == [PriceChange(price=20000, charges=None,
                                       first_seen_at="2026-10-01T06:00:00+00:00",
                                       last_seen_at="2026-10-03T06:00:00+00:00")]

    def test_starts_a_new_price_on_each_change_including_a_rise_back(self):
        changes = price_changes([_seen(1, 20000), _seen(2, 19000), _seen(3, 19000), _seen(4, 20000)])
        assert [(change.price, change.first_seen_at[:10], change.last_seen_at[:10]) for change in changes] == [
            (20000, "2026-10-01", "2026-10-01"),
            (19000, "2026-10-02", "2026-10-03"),
            (20000, "2026-10-04", "2026-10-04"),
        ]

    def test_keeps_the_charges_last_seen_at_a_price_without_splitting_it(self):
        changes = price_changes([_seen(1, 20000, charges=3000), _seen(2, 20000, charges=3500)])
        assert len(changes) == 1
        assert changes[0].charges == 3500

    def test_holds_no_prices_without_observations(self):
        assert price_changes([]) == []
