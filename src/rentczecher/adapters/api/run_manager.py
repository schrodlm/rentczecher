"""Runs one profile scrape at a time on a background worker thread,
publishing SSE events as it goes.

Serialization is a queue, not a lock-and-reject: every POST /v1/runs gets a
run id immediately, and the worker drains requests one at a time, so no two
pipeline runs ever execute concurrently regardless of how many requests
arrive close together.
"""

import logging
import queue
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import uuid4

from rentczecher.adapters.api.events import EventBroker, RunEvent
from rentczecher.domain.scrape import ScraperHealth
from rentczecher.services.pipeline import PipelineDeps, ProfileRunResult

log = logging.getLogger("rentczecher.api")


class PipelineRunner(Protocol):
    def __call__(
        self, profile_config: dict, deps: PipelineDeps, *, dry_run: bool = False,
        on_scraper_done: Callable[[str, ScraperHealth], None] | None = None,
    ) -> ProfileRunResult:
        ...


@dataclass(frozen=True, slots=True)
class _RunRequest:
    run_id: str
    profile_id: str
    profile_config: dict


@dataclass(frozen=True, slots=True)
class PortalHealthEntry:
    status: Literal["ok", "broken", "zero_results"]
    error: str | None
    listing_count: int
    checked_at: str


class RunManager:
    """Owns the worker thread and the run queue. profile_deps_for opens a
    fresh PipelineDeps per run (its own DB connection and HTTP client), so
    the worker thread never shares a connection with the request-handling
    thread.

    last_health tracks the most recent ScraperHealth seen per portal across
    every run, for GET /v1/health to read without waiting on a run."""

    def __init__(
        self,
        profile_deps_for: Callable[[str], AbstractContextManager[PipelineDeps]],
        broker: EventBroker,
        *,
        run_profile: PipelineRunner,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._profile_deps_for = profile_deps_for
        self._broker = broker
        self._run_profile = run_profile
        self._clock = clock
        self._health_lock = threading.Lock()
        self._last_health: dict[str, PortalHealthEntry] = {}
        self._queue: "queue.Queue[_RunRequest]" = queue.Queue()
        self._worker = threading.Thread(target=self._drain, name="rentczecher-run-worker", daemon=True)
        self._worker.start()

    def trigger(self, profile_id: str, profile_config: dict) -> str:
        run_id = str(uuid4())
        self._queue.put(_RunRequest(run_id=run_id, profile_id=profile_id, profile_config=profile_config))
        return run_id

    def last_health(self) -> dict[str, PortalHealthEntry]:
        with self._health_lock:
            return dict(self._last_health)

    def _record_health(self, scraper: str, health: ScraperHealth) -> None:
        entry = PortalHealthEntry(
            status=health.status, error=health.error, listing_count=health.listing_count,
            checked_at=self._clock().isoformat(),
        )
        with self._health_lock:
            self._last_health[scraper] = entry

    def _drain(self) -> None:
        while True:
            request = self._queue.get()
            self._run_one(request)

    def _run_one(self, request: _RunRequest) -> None:
        self._broker.publish(RunEvent(
            kind="run_started", data={"run_id": request.run_id, "profile_id": request.profile_id}))

        def on_scraper_done(scraper: str, health: ScraperHealth) -> None:
            self._record_health(scraper, health)
            self._broker.publish(RunEvent(
                kind="run_progress",
                data={
                    "run_id": request.run_id, "profile_id": request.profile_id, "scraper": scraper,
                    "status": health.status, "listing_count": health.listing_count,
                },
            ))

        try:
            with self._profile_deps_for(request.profile_id) as deps:
                result = self._run_profile(request.profile_config, deps, on_scraper_done=on_scraper_done)
        except Exception as error:
            log.exception("Run %s for profile %s failed", request.run_id, request.profile_id)
            self._broker.publish(RunEvent(
                kind="run_finished",
                data={"run_id": request.run_id, "profile_id": request.profile_id,
                     "status": "failed", "error": str(error)},
            ))
            return

        self._broker.publish(RunEvent(
            kind="run_finished",
            data={
                "run_id": request.run_id, "profile_id": request.profile_id,
                "status": result.status,
                "counts": {
                    "total": result.counts.total, "new": result.counts.new,
                    "price_drops": result.counts.price_drops, "disappeared": result.counts.disappeared,
                },
            },
        ))
        if result.counts.new:
            self._broker.publish(RunEvent(
                kind="listings_arrived",
                data={"run_id": request.run_id, "profile_id": request.profile_id, "new": result.counts.new},
            ))
