from abc import ABC, abstractmethod

import httpx

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.profile import Criteria

__all__ = ["BaseScraper", "Listing"]


class BaseScraper(ABC):
    name: str = "base"

    def __init__(self, criteria: Criteria, client: httpx.Client):
        self.criteria = criteria
        self._client = client

    @abstractmethod
    def scrape(self) -> list[Listing]:
        """Return all listings matching the search criteria."""
        ...
