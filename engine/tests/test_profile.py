"""Tests for a profile's criteria and preferences.

Run: python3 -m pytest tests/test_profile.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria
from tests.profiles import layouts, preferences


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
