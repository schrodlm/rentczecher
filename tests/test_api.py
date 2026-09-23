"""Tests for the sidecar API: auth and the routes over a real SQLite
database, driven through FastAPI's TestClient.

Run: python3 -m pytest tests/test_api.py -v
"""

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from rentczecher.adapters.api.app import create_app
from rentczecher.adapters.api.deps import ApiDeps
from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.dedup import DedupOutcome
from rentczecher.domain.scrape import ScraperHealth
from rentczecher.services.pipeline import ProfileRunResult, RunCounts

TOKEN = "test-token"
BASE = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)

PROFILE_CONFIG = {
    "praha7-byty": {
        "name": "Praha 7 byty",
        "enabled": True,
        "to": [],
        "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
        "scrapers": ["sreality"],
    },
    "domazlice-domy": {
        "name": "Domazlice domy",
        "enabled": False,
        "to": [],
        "search": {"offer_type": "sale", "estate_type": "house", "place": "domazlice"},
        "scrapers": ["sreality"],
    },
}


def _db(tmp_path: Path) -> Path:
    db_path = tmp_path / "t.db"
    conn = connection.connect(db_path)
    migrate.apply_pending(conn)
    conn.close()
    return db_path


def _api_deps(tmp_path: Path, profiles: dict | None = None) -> ApiDeps:
    return ApiDeps(
        config={"profiles": profiles if profiles is not None else PROFILE_CONFIG},
        db_path=_db(tmp_path),
        scrapers={},
    )


def _stub_run_profile(result: ProfileRunResult | None = None, *, error: Exception | None = None):
    """A services.pipeline.run_profile stand-in: records every call and
    returns a canned result (or raises), never touching a scraper."""
    calls = []

    def run_profile(profile_config, deps, *, dry_run=False, on_scraper_done=None):
        calls.append(profile_config["id"])
        if on_scraper_done is not None:
            on_scraper_done("sreality", ScraperHealth(status="ok", error=None, listing_count=2))
        if error is not None:
            raise error
        return result or ProfileRunResult(
            profile_id=profile_config["id"], run_id="stub-run", started_at=BASE, finished_at=BASE,
            status="ok", scraper_health={"sreality": ScraperHealth(status="ok", error=None, listing_count=2)},
            counts=RunCounts(total=2, new=2, price_drops=0, disappeared=0),
        )

    run_profile.calls = calls
    return run_profile


def _client(tmp_path: Path, *, profiles: dict | None = None, run_profile=None) -> TestClient:
    deps = _api_deps(tmp_path, profiles)
    app = create_app(TOKEN, deps, run_profile=run_profile or _stub_run_profile())
    return TestClient(app)


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


class TestAuth:
    def test_missing_token_is_rejected(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles")
        assert response.status_code == 401

    def test_wrong_token_is_rejected(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles", headers={"Authorization": "Bearer wrong"})
        assert response.status_code == 401

    def test_correct_token_is_accepted(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles", headers=_auth())
        assert response.status_code == 200

    def test_query_token_is_rejected_outside_the_event_stream_route(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles", params={"token": TOKEN})
        assert response.status_code == 401


class TestListProfiles:
    def test_returns_profiles_from_config_read_only(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles", headers=_auth())
        body = response.json()
        assert {p["id"] for p in body} == {"praha7-byty", "domazlice-domy"}
        disabled = next(p for p in body if p["id"] == "domazlice-domy")
        assert disabled["enabled"] is False


class TestListListings:
    def test_unknown_profile_is_404(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles/nope/listings", headers=_auth())
        assert response.status_code == 404

    def test_filter_new_excludes_viewed_listings(self, tmp_path):
        deps = _api_deps(tmp_path)
        with deps.open_run_store() as store:
            listing = Listing.build(
                id="sreality:1", source="sreality", title="t", price=20000, location="l",
                url="https://example.com/1")
            store.persist_outcome(
                "praha7-byty", "Praha 7 byty", DedupOutcome(survivors=[listing], merges=(), uncertain=()),
                {}, current_ids={"sreality:1"})
            store.mark_viewed("praha7-byty", "sreality:1")

        app = create_app(TOKEN, deps, run_profile=_stub_run_profile())
        client = TestClient(app)

        new_only = client.get("/v1/profiles/praha7-byty/listings", headers=_auth(), params={"filter": "new"})
        assert new_only.json() == []

        every = client.get("/v1/profiles/praha7-byty/listings", headers=_auth(), params={"filter": "all"})
        assert [card["id"] for card in every.json()] == ["sreality:1"]
        assert every.json()[0]["viewed_at"] is not None


class TestMarkViewed:
    def test_unknown_profile_is_404(self, tmp_path):
        client = _client(tmp_path)
        response = client.patch("/v1/profiles/nope/listings/sreality:1/viewed", headers=_auth())
        assert response.status_code == 404

    def test_marks_the_listing_viewed(self, tmp_path):
        deps = _api_deps(tmp_path)
        with deps.open_run_store() as store:
            listing = Listing.build(
                id="sreality:1", source="sreality", title="t", price=20000, location="l",
                url="https://example.com/1")
            store.persist_outcome(
                "praha7-byty", "Praha 7 byty", DedupOutcome(survivors=[listing], merges=(), uncertain=()),
                {}, current_ids={"sreality:1"})

        app = create_app(TOKEN, deps, run_profile=_stub_run_profile())
        client = TestClient(app)

        response = client.patch("/v1/profiles/praha7-byty/listings/sreality:1/viewed", headers=_auth())
        assert response.status_code == 204

        listings = client.get(
            "/v1/profiles/praha7-byty/listings", headers=_auth(), params={"filter": "all"}).json()
        assert listings[0]["viewed_at"] is not None


class TestTriggerRun:
    def test_unknown_profile_is_404(self, tmp_path):
        client = _client(tmp_path)
        response = client.post("/v1/runs", headers=_auth(), json={"profile_id": "nope"})
        assert response.status_code == 404

    def test_returns_a_run_id_immediately(self, tmp_path):
        run_profile = _stub_run_profile()
        client = _client(tmp_path, run_profile=run_profile)
        response = client.post("/v1/runs", headers=_auth(), json={"profile_id": "praha7-byty"})
        assert response.status_code == 202
        body = response.json()
        assert body["profile_id"] == "praha7-byty"
        assert body["run_id"]

    def test_missing_profile_id_is_a_validation_error(self, tmp_path):
        client = _client(tmp_path)
        response = client.post("/v1/runs", headers=_auth(), json={})
        assert response.status_code == 422

    def test_concurrent_requests_never_run_the_pipeline_at_the_same_time(self, tmp_path):
        overlap_detected = threading.Event()
        currently_running = threading.Event()

        def run_profile(profile_config, deps, *, dry_run=False, on_scraper_done=None):
            if currently_running.is_set():
                overlap_detected.set()
            currently_running.set()
            time.sleep(0.2)
            currently_running.clear()
            return ProfileRunResult(
                profile_id=profile_config["id"], run_id="r", started_at=BASE, finished_at=BASE,
                status="ok", scraper_health={}, counts=RunCounts(total=0, new=0, price_drops=0, disappeared=0),
            )

        client = _client(tmp_path, run_profile=run_profile)
        responses = [
            client.post("/v1/runs", headers=_auth(), json={"profile_id": "praha7-byty"})
            for _ in range(3)
        ]
        assert all(r.status_code == 202 for r in responses)
        time.sleep(1.0)
        assert not overlap_detected.is_set()


class TestHealth:
    def test_empty_before_any_run(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/health", headers=_auth())
        assert response.json() == []

    def test_reflects_the_last_run_per_portal(self, tmp_path):
        run_profile = _stub_run_profile()
        client = _client(tmp_path, run_profile=run_profile)
        client.post("/v1/runs", headers=_auth(), json={"profile_id": "praha7-byty"})

        deadline = time.monotonic() + 3
        body: list = []
        while time.monotonic() < deadline:
            body = client.get("/v1/health", headers=_auth()).json()
            if body:
                break
            time.sleep(0.05)

        assert len(body) == 1
        assert body[0]["portal"] == "sreality"
        assert body[0]["status"] == "ok"
        assert body[0]["listing_count"] == 2
