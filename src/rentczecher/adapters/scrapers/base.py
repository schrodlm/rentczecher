from abc import ABC, abstractmethod

import httpx

from rentczecher.domain.listing import Listing

__all__ = ["BaseScraper", "Listing", "ScraperBrokenError"]


class ScraperBrokenError(Exception):
    """The portal responded, but not in the shape this scraper understands."""


class BaseScraper(ABC):
    name: str = "base"

    def __init__(self, profile: dict, client: httpx.Client):
        self.profile = profile
        self._client = client
        search = profile.get("search", {})
        self.min_price = search.get("min_price", 0)
        self.max_price = search.get("max_price", 25000)
        self.scraper_cfg = profile.get("scrapers", {}).get(self.name, {})

    @abstractmethod
    def scrape(self) -> list[Listing]:
        """Return all listings matching the search criteria."""
        ...
