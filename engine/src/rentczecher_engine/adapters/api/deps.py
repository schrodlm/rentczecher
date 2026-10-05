"""The long-lived facts every part of the server needs: the database path
and the scraper registry. Everything stateful, such as a connection or an
HTTP client, is deliberately not held here but opened fresh on demand by
the factory methods. Profiles are read from the database on every request.

A fresh sqlite3.Connection, Gazetteer, and httpx.Client are opened per run
rather than shared, because the run executes on the worker thread and
sqlite3 connections (the gazetteer is one) are not safe to hand across
threads.
"""

from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.adapters.repositories.sqlite import connection
from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.adapters.repositories.sqlite.profiles import SqliteProfileRepository
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher_engine.adapters.scrapers.client import build_client
from rentczecher_engine.domain.errors import ProfileNotFoundError
from rentczecher_engine.domain.profile import Criteria, Profile
from rentczecher_engine.services.pipeline import PipelineDeps
from rentczecher_engine.services.scrape import Scraper


@dataclass(frozen=True, slots=True)
class ApiDeps:
    db_path: Path
    scrapers: dict[str, Callable[[Criteria, object], Scraper]]
    gazetteer_db_path: Path | None = None

    def list_profiles(self) -> list[Profile]:
        with closing(connection.connect(self.db_path)) as conn:
            return SqliteProfileRepository(conn).list_profiles()

    def profile(self, profile_id: str) -> Profile | None:
        with closing(connection.connect(self.db_path)) as conn:
            return SqliteProfileRepository(conn).get(profile_id)

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
    def open_gazetteer(self) -> Iterator[Gazetteer]:
        """A gazetteer on its own connection, closed when the caller is done."""
        with closing(Gazetteer(self.gazetteer_db_path)) as gazetteer:
            yield gazetteer

    @contextmanager
    def build_pipeline_deps(self) -> Iterator[PipelineDeps]:
        """A run's own connection, gazetteer and HTTP client, never shared
        with request handlers and all closed when the run finishes."""
        conn = connection.connect(self.db_path)
        try:
            with self.open_gazetteer() as gazetteer, build_client() as client:
                yield PipelineDeps(
                    store=SqliteRunStore(conn),
                    clock=utc_now,
                    client=client,
                    scrapers=self.scrapers,
                    gazetteer=gazetteer,
                )
        finally:
            conn.close()


def require_profile(deps: ApiDeps, profile_id: str) -> Profile:
    """The profile, or ProfileNotFoundError, which the app answers with a 404."""
    profile = deps.profile(profile_id)
    if profile is None:
        raise ProfileNotFoundError(profile_id)
    return profile


def resolve_profile(profile_id: str, request: Request) -> Profile:
    """A path-based route dependency wrapping require_profile, for routes
    where profile_id is a path parameter FastAPI can inject directly."""
    deps: ApiDeps = request.app.state.api_deps
    return require_profile(deps, profile_id)
