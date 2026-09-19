"""The pipeline's own view of what it reads and persists, and the shape of
what one profile run reports back.

RunStore is a structural Protocol, not an inheritance contract, so an
adapter-side store type can satisfy it without this module ever importing
that adapter.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable
from uuid import uuid4

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.domain.dedup import DedupOutcome
from rentczecher.domain.errors import PlaceNotFoundError
from rentczecher.domain.listing import DisappearedListing, Listing
from rentczecher.domain.scrape import ScraperHealth
from rentczecher.domain.search import SearchSpec
from rentczecher.services.dedup import cross_source_dedup
from rentczecher.services.diff import classify
from rentczecher.services.filters import apply_filters
from rentczecher.services.locate import locate_listings
from rentczecher.services.scrape import Scraper, scrape_all
from rentczecher.services.score import compute_score

log = logging.getLogger("rentczecher")


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
    client: object
    scrapers: Mapping[str, Callable[[SearchSpec, object], Scraper]]
    gazetteer: Gazetteer
    notify: Callable[[list[Listing], SearchSpec, dict, list[DisappearedListing]], object]


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
    error: str | None = None


def _status_for(scraper_health: dict[str, ScraperHealth]) -> Literal["ok", "partial"]:
    if any(health.status == "broken" for health in scraper_health.values()):
        return "partial"
    return "ok"


def _failed_result(profile_id: str, run_id: str, started_at: datetime,
                   finished_at: datetime, error: str) -> ProfileRunResult:
    return ProfileRunResult(
        profile_id=profile_id, run_id=run_id, started_at=started_at, finished_at=finished_at,
        status="failed", scraper_health={}, counts=RunCounts(total=0, new=0, price_drops=0, disappeared=0),
        error=error,
    )


def _notify_succeeded(notify: Callable[..., object], notable: list[Listing],
                      spec: SearchSpec, profile_config: dict,
                      disappeared: list[DisappearedListing]) -> bool:
    """Nothing to say is not a failure to say it - persisting still runs.
    A real send failing is signalled by raising or by returning False."""
    if not notable:
        return True
    return notify(notable, spec, profile_config, disappeared) is not False


def _has_recipients(profile_config: dict) -> bool:
    return bool(profile_config.get("to", []))


def run_profile(profile_config: dict, deps: PipelineDeps, *, dry_run: bool = False) -> ProfileRunResult:
    profile_id = profile_config["id"]
    run_id = str(uuid4())
    started_at = deps.clock()
    spec = SearchSpec.from_search_config(profile_config["search"])

    enabled = {name: cls for name, cls in deps.scrapers.items()
              if name in profile_config["scrapers"]}
    try:
        scraped, scraper_health = scrape_all(enabled, spec, deps.client)
    except PlaceNotFoundError as error:
        log.error("Profile %s: %s - fix search.place", profile_id, error)
        return _failed_result(profile_id, run_id, started_at, deps.clock(), str(error))

    filtered = apply_filters(scraped, spec)
    located = locate_listings(filtered, deps.gazetteer)

    located_by_id = {listing.id: listing for listing in located}
    outcome = cross_source_dedup(located, deps.gazetteer)
    survivors = [listing.with_annotations(score=compute_score(listing, profile_config))
                for listing in outcome.survivors]

    current_ids = {listing.id for listing in survivors} | {m.absorbed_id for m in outcome.merges}
    disappeared = deps.store.pending_disappeared(profile_id, current_ids)
    diff = classify(survivors, deps.store.seen_ids(profile_id),
                    deps.store.latest_prices(profile_id), disappeared)
    notable = diff.new + diff.price_drops

    if not dry_run and _notify_succeeded(deps.notify, notable, spec, profile_config, diff.disappeared):
        deps.store.persist_outcome(
            profile_id, profile_config["name"], outcome, located_by_id, current_ids)
        if notable and _has_recipients(profile_config):
            deps.store.prune(profile_id)

    finished_at = deps.clock()
    counts = RunCounts(total=len(survivors), new=len(diff.new),
                       price_drops=len(diff.price_drops), disappeared=len(diff.disappeared))
    return ProfileRunResult(
        profile_id=profile_id, run_id=run_id, started_at=started_at, finished_at=finished_at,
        status=_status_for(scraper_health), scraper_health=scraper_health, counts=counts,
    )
