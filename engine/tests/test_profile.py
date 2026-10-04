"""Tests for the portal-neutral Criteria.

Run: python3 -m pytest tests/test_profile.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria


class TestFromSearchConfig:
    """A validated config's search section maps onto the criteria field-for-field."""

    def test_maps_all_fields(self):
        criteria = Criteria.from_search_config({
            "offer_type": "rent",
            "estate_type": "flat",
            "place": PlaceRef("obvod", 78),
            "min_price": 17000,
            "max_price": 25000,
            "min_size_m2": 30,
            "min_land_m2": 500,
            "dispositions": ["2+kk", "2+1"],
        })
        assert criteria.offer_type == "rent"
        assert criteria.estate_type == "flat"
        assert criteria.place == PlaceRef("obvod", 78)
        assert criteria.min_price == 17000
        assert criteria.max_price == 25000
        assert criteria.min_size_m2 == 30
        assert criteria.min_land_m2 == 500
        assert criteria.dispositions == ("2+kk", "2+1")

    def test_absent_bounds_mean_unbounded(self):
        criteria = Criteria.from_search_config(
            {"offer_type": "sale", "estate_type": "house", "place": PlaceRef("okres", 3401)})
        assert criteria.min_price == 0
        assert criteria.max_price == 0
        assert criteria.min_size_m2 == 0
        assert criteria.min_land_m2 == 0
        assert criteria.dispositions == ()

    def test_offer_estate_type_and_place_are_required(self):
        with pytest.raises(KeyError):
            Criteria.from_search_config({"estate_type": "flat", "place": PlaceRef("obvod", 78)})
        with pytest.raises(KeyError):
            Criteria.from_search_config({"offer_type": "rent", "place": PlaceRef("obvod", 78)})
        with pytest.raises(KeyError):
            Criteria.from_search_config({"offer_type": "rent", "estate_type": "flat"})


class TestImmutability:
    """The criteria are frozen: search intent cannot drift mid-run."""

    def test_fields_cannot_be_reassigned(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        with pytest.raises(dataclasses.FrozenInstanceError):
            criteria.max_price = 1  # type: ignore[misc]

    def test_dispositions_are_a_tuple_even_from_a_list(self):
        criteria = Criteria.from_search_config({
            "offer_type": "rent", "estate_type": "flat", "place": PlaceRef("obvod", 78),
            "dispositions": ["2+kk"],
        })
        assert isinstance(criteria.dispositions, tuple)
