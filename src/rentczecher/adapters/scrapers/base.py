from abc import ABC, abstractmethod

from rentczecher.domain.listing import Listing

__all__ = ["BaseScraper", "Listing"]


class BaseScraper(ABC):
    name: str = "base"

    def __init__(self, profile: dict):
        self.profile = profile
        search = profile.get("search", {})
        self.min_price = search.get("min_price", 0)
        self.max_price = search.get("max_price", 25000)
        self.scraper_cfg = profile.get("scrapers", {}).get(self.name, {})

    @abstractmethod
    def scrape(self) -> list[Listing]:
        """Return all listings matching the search criteria."""
        ...
