"""Tests for the disposition layout normalizer.

Run: python3 -m pytest tests/test_domain_disposition.py -v
"""

import pytest

from rentczecher.domain.disposition import normalize_disposition


class TestFlatLayouts:
    def test_canonical_forms_pass_through(self):
        assert normalize_disposition("2+kk") == "2+kk"
        assert normalize_disposition("3+1") == "3+1"

    def test_case_and_spacing_normalize(self):
        assert normalize_disposition("2+KK") == "2+kk"
        assert normalize_disposition("2 + kk") == "2+kk"

    @pytest.mark.parametrize("studio", ["garsoniéra", "Garsoniéra", "garsoniera", "garsonka"])
    def test_studio_synonyms_are_1kk(self, studio):
        assert normalize_disposition(studio) == "1+kk"

    def test_atypical_normalizes_with_diacritics(self):
        assert normalize_disposition("Atypický") == "atypicky"

    def test_unknown_string_is_no_evidence(self):
        assert normalize_disposition("Rodinný") is None

    def test_missing_is_no_evidence(self):
        assert normalize_disposition(None) is None
        assert normalize_disposition("") is None


class TestSelfIdentifyingLayouts:
    """Layout strings identify themselves regardless of estate type; a
    building-type label never parses as one."""

    def test_house_layout_normalizes(self):
        assert normalize_disposition("4+kk") == "4+kk"

    def test_building_type_label_is_no_evidence(self):
        assert normalize_disposition("Rodinný") is None
