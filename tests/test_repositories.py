"""The repository interfaces are abstract contracts.

Run: python3 -m pytest tests/test_repositories.py -v
"""

import pytest

from rentczecher.adapters.repositories.repositories import (
    ListingRepository,
    PropertyRepository,
)


@pytest.mark.parametrize("repo", [ListingRepository, PropertyRepository])
def test_cannot_instantiate_the_abstract_interface(repo):
    with pytest.raises(TypeError):
        repo()


def test_a_partial_implementation_is_rejected_at_construction():
    class Half(PropertyRepository):
        def get(self, property_id):
            return None
        # create / attach_listing / record_dedup left unimplemented

    with pytest.raises(TypeError, match="abstract"):
        Half()
