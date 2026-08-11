"""Tests for the PriceObservation record.

Run: python3 -m pytest tests/test_domain_price.py -v
"""

import dataclasses

import pytest

from rentczecher.domain.price import PriceObservation


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
