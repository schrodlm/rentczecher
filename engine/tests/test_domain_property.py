"""Tests for the PropertyIdentity record.

Run: python3 -m pytest tests/test_domain_property.py -v
"""

import dataclasses

import pytest

from rentczecher.domain.property import PropertyIdentity


def test_is_immutable():
    p = PropertyIdentity(id="x", created_at="2026-08-11T06:00:00+00:00")
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.title = "changed"  # type: ignore[misc]


def test_facts_and_merged_into_default_to_none():
    p = PropertyIdentity(id="x", created_at="2026-08-11T06:00:00+00:00")
    assert p.merged_into is None
    assert p.title is None and p.size_m2 is None and p.lat is None


def test_carries_canonical_facts():
    p = PropertyIdentity(id="x", created_at="2026-08-11T06:00:00+00:00",
                         title="Byt 2+kk", size_m2=55, disposition="2+kk")
    assert p.title == "Byt 2+kk"
    assert p.size_m2 == 55
    assert p.disposition == "2+kk"
