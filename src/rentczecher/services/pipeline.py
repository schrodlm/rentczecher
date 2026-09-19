"""The pipeline's own view of what it reads and persists, and the shape of
what one profile run reports back.

RunStore is a structural Protocol, not an inheritance contract, so an
adapter-side store type can satisfy it without this module ever importing
that adapter.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from rentczecher.domain.dedup import DedupOutcome
from rentczecher.domain.listing import DisappearedListing, Listing
from rentczecher.domain.scrape import ScraperHealth


@runtime_checkable
class RunStore(Protocol):
    def seen_ids(self, profile_id: str) -> set[str]:
        ...

    def latest_prices(self, profile_id: str) -> dict[str, int]:
        ...

    def pending_disappeared(self, profile_id: str, current_ids: set[str]) -> list[DisappearedListing]:
        ...

    def prune(self, profile_id: str) -> None:
        ...

    def persist_outcome(self, profile_id: str, profile_name: str, outcome: DedupOutcome,
                        located_by_id: dict[str, Listing], current_ids: set[str]) -> None:
        ...


@dataclass(frozen=True, slots=True)
class PipelineDeps:
    store: RunStore
    clock: Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class RunCounts:
    total: int
    new: int
    price_drops: int
    disappeared: int


@dataclass(frozen=True, slots=True)
class ProfileRunResult:
    profile_id: str
    run_id: str
    started_at: datetime
    finished_at: datetime
    status: Literal["ok", "partial", "failed"]
    scraper_health: dict[str, ScraperHealth]
    counts: RunCounts
