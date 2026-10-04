"""Tests for parsing a scraped disposition into a layout.

Run: python3 -m pytest tests/test_domain_disposition.py -v
"""

import pytest

from rentczecher_engine.domain.disposition import ATYPICAL, Disposition, parse_disposition


def _code(raw: str | None) -> str | None:
    disposition = parse_disposition(raw)
    return disposition.code if disposition is not None else None


class TestFlatLayouts:
    def test_canonical_forms_pass_through(self):
        assert _code("2+kk") == "2+kk"
        assert _code("3+1") == "3+1"

    def test_case_and_spacing_normalize(self):
        assert _code("2+KK") == "2+kk"
        assert _code("2 + kk") == "2+kk"

    @pytest.mark.parametrize("studio", ["garsoniéra", "Garsoniéra", "garsoniera", "garsonka"])
    def test_studio_synonyms_are_1kk(self, studio):
        assert _code(studio) == "1+kk"

    def test_atypical_normalizes_with_diacritics(self):
        assert _code("Atypický") == "atypicky"

    def test_unknown_string_is_no_evidence(self):
        assert _code("Rodinný") is None

    def test_missing_is_no_evidence(self):
        assert _code(None) is None
        assert _code("") is None


class TestSelfIdentifyingLayouts:
    """Layout strings identify themselves regardless of estate type; a
    building-type label never parses as one."""

    def test_house_layout_normalizes(self):
        assert _code("4+kk") == "4+kk"

    def test_building_type_label_is_no_evidence(self):
        assert _code("Rodinný") is None


class TestParsedLayout:
    def test_layout_carries_its_rooms_and_kitchen_kind(self):
        assert parse_disposition("2+kk") == Disposition(rooms=2, kitchen="kitchenette")
        assert parse_disposition("2+1") == Disposition(rooms=2, kitchen="separate")

    def test_atypical_parses_to_the_atypical_layout(self):
        assert parse_disposition("Atypický") == ATYPICAL

    @pytest.mark.parametrize("raw", ["3+2", "3+0"])
    def test_second_number_other_than_one_names_no_kitchen(self, raw):
        assert parse_disposition(raw) is None

    def test_rooms_run_from_one_to_nine(self):
        assert parse_disposition("9+1") == Disposition(rooms=9, kitchen="separate")
        assert parse_disposition("0+kk") is None


class TestDisposition:
    def test_half_filled_disposition_is_refused(self):
        with pytest.raises(ValueError):
            Disposition(rooms=2, kitchen=None)
        with pytest.raises(ValueError):
            Disposition(rooms=None, kitchen="separate")
