"""Tests for a profile's criteria and preferences.

Run: python3 -m pytest tests/test_profile.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria
from tests.profiles import criteria, layouts, preferences, profile


class TestImmutability:
    """The criteria are frozen: search intent cannot drift mid-run."""

    def test_fields_cannot_be_reassigned(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        with pytest.raises(dataclasses.FrozenInstanceError):
            criteria.max_price = 1  # type: ignore[misc]


class TestPreferenceSettings:
    """A weighted preference needs its setting. Only an unweighted one may
    leave it empty."""

    @pytest.mark.parametrize(("weight", "setting", "message"), [
        ("disposition_weight", {}, "disposition_weight needs preferred_dispositions"),
        ("size_weight", {}, "size_weight needs a positive ideal_size_m2"),
        ("size_weight", {"ideal_size_m2": 0}, "size_weight needs a positive ideal_size_m2"),
        ("place_weight", {}, "place_weight needs preferred_places"),
        ("land_weight", {}, "land_weight needs a positive ideal_land_m2"),
        ("land_weight", {"ideal_land_m2": -1}, "land_weight needs a positive ideal_land_m2"),
        ("price_weight", {}, "price_weight needs a positive max_good_price"),
        ("price_weight", {"max_good_price": 0}, "price_weight needs a positive max_good_price"),
    ])
    def test_a_weighted_preference_without_its_setting_is_rejected(self, weight, setting, message):
        with pytest.raises(ValueError, match=message):
            preferences(**{weight: 10}, **setting)

    def test_an_unweighted_preference_may_leave_its_setting_empty(self):
        preferences(ideal_size_m2=0, ideal_land_m2=-1, max_good_price=-1)

    def test_a_weighted_preference_with_its_setting_is_accepted(self):
        preferences(disposition_weight=10, preferred_dispositions=layouts("2+kk"),
                    size_weight=10, ideal_size_m2=1,
                    place_weight=10, preferred_places=(PlaceRef("obvod", 78),),
                    land_weight=10, ideal_land_m2=1,
                    price_weight=10, max_good_price=1)


class TestCriteriaBounds:
    """A bound is positive or unset, unset being the only way to say no
    bound. Rooms run 1 to 9, and a range never runs backwards."""

    @pytest.mark.parametrize("bound", ["min_price", "max_price", "min_size_m2", "min_land_m2"])
    @pytest.mark.parametrize("value", [0, -1])
    def test_a_bound_of_zero_or_less_is_rejected(self, bound, value):
        with pytest.raises(ValueError, match=f"{bound} must be positive"):
            criteria(**{bound: value})

    @pytest.mark.parametrize("bound", ["min_rooms", "max_rooms"])
    @pytest.mark.parametrize("rooms", [0, 10])
    def test_a_room_count_outside_one_to_nine_is_rejected(self, bound, rooms):
        with pytest.raises(ValueError, match=f"{bound} must be 1 to 9"):
            criteria(**{bound: rooms})

    @pytest.mark.parametrize(("low", "high"), [("min_price", "max_price"), ("min_rooms", "max_rooms")])
    def test_a_range_running_backwards_is_rejected(self, low, high):
        with pytest.raises(ValueError, match=f"{low} must not exceed {high}"):
            criteria(**{low: 3, high: 2})

    @pytest.mark.parametrize("rooms", [1, 9])
    def test_a_range_of_one_room_count_at_either_end_is_accepted(self, rooms):
        criteria(min_rooms=rooms, max_rooms=rooms)

    def test_a_bound_of_one_is_accepted(self):
        criteria(min_price=1, max_price=1, min_size_m2=1, min_land_m2=1)


class TestUniqueEntries:
    """A list in a profile names each entry once."""

    def test_a_repeated_preferred_disposition_is_rejected(self):
        """A garsoniéra is a 1+kk, so listing both repeats a layout."""
        with pytest.raises(ValueError, match="preferred_dispositions must not repeat"):
            preferences(preferred_dispositions=layouts("garsoniéra", "1+kk"))

    def test_a_repeated_preferred_place_is_rejected(self):
        with pytest.raises(ValueError, match="preferred_places must not repeat"):
            preferences(preferred_places=(PlaceRef("obvod", 78), PlaceRef("obvod", 78)))

    def test_the_same_code_under_two_kinds_is_accepted(self):
        preferences(preferred_places=(PlaceRef("obvod", 78), PlaceRef("cast_obce", 78)))

    def test_a_repeated_portal_is_rejected(self):
        with pytest.raises(ValueError, match="portals must not repeat"):
            profile(portals=("sreality", "sreality"))
