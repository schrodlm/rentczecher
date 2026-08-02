from abc import ABC, abstractmethod

import httpx

from rentczecher.domain.listing import Listing
from rentczecher.domain.search import SearchSpec

__all__ = ["BaseScraper", "Listing", "ScraperBrokenError"]


class ScraperBrokenError(Exception):
    """The portal responded, but not in the shape this scraper understands."""


class BaseScraper(ABC):
    name: str = "base"

    def __init__(self, spec: SearchSpec, client: httpx.Client):
        self.spec = spec
        self._client = client

    @abstractmethod
    def scrape(self) -> list[Listing]:
        """Return all listings matching the search criteria."""
        ...
