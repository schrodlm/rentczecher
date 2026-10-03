"""Tests for the PropertyIdentity and PropertyLocation records.

Run: python3 -m pytest tests/test_domain_property.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.domain.property import PropertyIdentity, PropertyLocation


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


def _location(**kw):
    fields = dict(kraj_code=19, okres_code=None, obec_code=554782, obvod_code=None, mestska_cast_code=None,
                  cast_obce_code=None, ulice_code=None, cislo_popisne=None, cislo_orientacni=None)
    fields.update(kw)
    return PropertyLocation(**fields)


class TestPropertyLocationDetail:
    def test_a_finer_unit_is_more_detailed(self):
        assert _location(ulice_code=467103).is_more_detailed_than(_location(cast_obce_code=490067))

    def test_between_equally_fine_units_a_house_number_is_more_detailed(self):
        assert _location(ulice_code=467103, cislo_popisne="1401").is_more_detailed_than(
            _location(ulice_code=467103))

    def test_a_finer_unit_outranks_a_house_number(self):
        assert _location(ulice_code=467103).is_more_detailed_than(
            _location(cast_obce_code=490067, cislo_popisne="1401"))

    def test_an_equal_location_is_not_more_detailed(self):
        assert not _location(ulice_code=467103).is_more_detailed_than(_location(ulice_code=467103))
