"""The long-lived facts every part of the server needs: the loaded config,
the database path, and the scraper registry. Everything stateful - a
connection, an HTTP client - is deliberately not held here but opened
fresh on demand by the two factory methods.

A fresh sqlite3.Connection, Gazetteer, and httpx.Client are opened per run
rather than shared, because the run executes on the worker thread and
sqlite3 connections (the gazetteer is one) are not safe to hand across
threads.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.notifiers.smtp import NoRecipientsNotifier, build_smtp_notifier
from rentczecher.adapters.repositories.sqlite import connection
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher.adapters.scrapers.client import build_client
from rentczecher.domain.search import SearchSpec
from rentczecher.services.pipeline import PipelineDeps
from rentczecher.services.scrape import Scraper


@dataclass(frozen=True, slots=True)
class ApiDeps:
    config: dict
    db_path: Path
    scrapers: dict[str, Callable[[SearchSpec, object], Scraper]]
    gazetteer_db_path: Path | None = None

    def profile_config(self, profile_id: str) -> dict | None:
        profile = self.config.get("profiles", {}).get(profile_id)
        if profile is None:
            return None
        return {**profile, "id": profile_id}

    @contextmanager
    def open_run_store(self) -> Iterator[SqliteRunStore]:
        """A store over its own connection, closed when the caller is done
        reading - a request handler opens one, reads, and lets it go."""
        conn = connection.connect(self.db_path)
        try:
            yield SqliteRunStore(conn)
        finally:
            conn.close()

    @contextmanager
    def build_pipeline_deps(self, profile_id: str) -> Iterator[PipelineDeps]:
        """A run's own connection and HTTP client, both closed when the run
        finishes - a fresh pair per call, never shared with the
        request-handling thread's connections."""
        profile = self.profile_config(profile_id)
        if profile is None:
            raise KeyError(profile_id)
        conn = connection.connect(self.db_path)
        try:
            with build_client() as client:
                email_cfg = self.config.get("email", {})
                notifier = build_smtp_notifier(
                    email_cfg, profile_id, profile.get("to", [])) or NoRecipientsNotifier(profile_id)
                yield PipelineDeps(
                    store=SqliteRunStore(conn),
                    clock=utc_now,
                    client=client,
                    scrapers=self.scrapers,
                    gazetteer=Gazetteer(self.gazetteer_db_path),
                    notifier=notifier,
                )
        finally:
            conn.close()


def require_profile(deps: ApiDeps, profile_id: str) -> dict:
    """Looks up a profile or raises the 404 every route needs on an unknown
    profile_id, so the check has one home instead of one per route."""
    profile = deps.profile_config(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"unknown profile {profile_id!r}")
    return profile


def resolve_profile(profile_id: str, request: Request) -> dict:
    """A path-based route dependency wrapping require_profile, for routes
    where profile_id is a path parameter FastAPI can inject directly."""
    deps: ApiDeps = request.app.state.api_deps
    return require_profile(deps, profile_id)
