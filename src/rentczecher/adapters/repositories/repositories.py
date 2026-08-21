"""Storage interfaces the pipeline will depend on; a SQLite implementation
lives behind them."""

from abc import ABC, abstractmethod

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.price import PriceObservation
from rentczecher.domain.property import PropertyIdentity


class PropertyRepository(ABC):
    @abstractmethod
    def get(self, property_id: str) -> PropertyIdentity | None:
        ...

    @abstractmethod
    def create(self, identity: PropertyIdentity) -> None:
        ...

    @abstractmethod
    def attach_listing(self, property_id: str, listing_id: str) -> None:
        """Point a listing at its property (a bare FK write; matching policy
        is the caller's)."""

    @abstractmethod
    def record_dedup(self, property_id: str, listing_id: str, match_reason: str,
                     differences: dict | None = None) -> None:
        """Log why a listing was judged the same property and how its facts
        diverged from canonical."""

    @abstractmethod
    def find_candidates(self, cell_lat: int, cell_lon: int) -> list[PropertyIdentity]:
        """Live properties whose geocell is the given cell or one of its
        eight neighbors - a recall-only blocking step, never a match
        decision."""


class ListingRepository(ABC):
    @abstractmethod
    def seen_ids(self, profile_id: str) -> set[str]:
        ...

    @abstractmethod
    def upsert(self, profile_id: str, property_id: str, listing: Listing) -> None:
        """Reconcile a scraped observation into storage: the thin listing row
        plus an appended price observation."""

    @abstractmethod
    def record_price_observation(self, observation: PriceObservation) -> None:
        ...

    @abstractmethod
    def price_history(self, listing_id: str) -> list[PriceObservation]:
        ...

    @abstractmethod
    def increment_miss_counts(self, profile_id: str, current_ids: set[str]) -> None:
        ...

    @abstractmethod
    def get_disappeared(self, profile_id: str, current_ids: set[str],
                        max_age_days: int = 7, min_misses: int = 3) -> list[dict]:
        ...

    @abstractmethod
    def prune(self, profile_id: str, max_age_days: int = 90) -> int:
        ...
