"""Tests for the portal-neutral SearchSpec.

Run: python3 -m pytest tests/test_domain_search.py -v
"""

import dataclasses

import pytest

from rentczecher.domain.search import SearchSpec


class TestFromSearchConfig:
    """A validated config's search section maps onto the spec field-for-field."""

    def test_maps_all_fields(self):
        spec = SearchSpec.from_search_config({
            "offer_type": "rent",
            "estate_type": "flat",
            "min_price": 17000,
            "max_price": 25000,
            "min_size_m2": 30,
            "min_land_m2": 500,
            "dispositions": ["2+kk", "2+1"],
        })
        assert spec.offer_type == "rent"
        assert spec.estate_type == "flat"
        assert spec.min_price == 17000
        assert spec.max_price == 25000
        assert spec.min_size_m2 == 30
        assert spec.min_land_m2 == 500
        assert spec.dispositions == ("2+kk", "2+1")

    def test_absent_bounds_mean_unbounded(self):
        spec = SearchSpec.from_search_config({"offer_type": "sale", "estate_type": "house"})
        assert spec.min_price == 0
        assert spec.max_price == 0
        assert spec.min_size_m2 == 0
        assert spec.min_land_m2 == 0
        assert spec.dispositions == ()

    def test_offer_and_estate_type_are_required(self):
        with pytest.raises(KeyError):
            SearchSpec.from_search_config({"estate_type": "flat"})
        with pytest.raises(KeyError):
            SearchSpec.from_search_config({"offer_type": "rent"})


class TestImmutability:
    """The spec is frozen: search intent cannot drift mid-run."""

    def test_fields_cannot_be_reassigned(self):
        spec = SearchSpec(offer_type="rent", estate_type="flat")
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.max_price = 1  # type: ignore[misc]

    def test_dispositions_are_a_tuple_even_from_a_list(self):
        spec = SearchSpec.from_search_config({
            "offer_type": "rent", "estate_type": "flat", "dispositions": ["2+kk"],
        })
        assert isinstance(spec.dispositions, tuple)
