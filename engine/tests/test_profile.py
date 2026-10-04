"""Tests for the portal-neutral Criteria.

Run: python3 -m pytest tests/test_profile.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria


class TestImmutability:
    """The criteria are frozen: search intent cannot drift mid-run."""

    def test_fields_cannot_be_reassigned(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        with pytest.raises(dataclasses.FrozenInstanceError):
            criteria.max_price = 1  # type: ignore[misc]
