"""Tests for the sidecar API: auth, the routes over a real SQLite database,
run-now serialization, and the SSE event stream.

The FastAPI TestClient in this environment buffers a streamed response
until the ASGI app's coroutine returns, so it cannot drive a route whose
generator runs forever. GET /v1/events is therefore exercised at the
generator level (iter_sse_events) rather than through the test client.

Run: python3 -m pytest tests/test_api.py -v
"""

import threading
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rentczecher_engine.adapters.api.app import create_app
from rentczecher_engine.adapters.api.auth import BearerOrQueryTokenAuth
from rentczecher_engine.adapters.api.deps import ApiDeps
from rentczecher_engine.adapters.api.events import EventBroker, RunEvent
from rentczecher_engine.adapters.api.routes.events import iter_sse_events
from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.domain.dedup import DedupOutcome
from rentczecher_engine.domain.location import Location, ParsedPlace, PlaceRef
from rentczecher_engine.domain.profile import Profile
from rentczecher_engine.domain.scrape import ScraperHealth
from rentczecher_engine.services.pipeline import ProfileRunResult, RunCounts
from tests.profiles import criteria, stored_profile

TOKEN = "test-token"
BASE = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)


def _db(tmp_path: Path) -> Path:
    db_path = tmp_path / "t.db"
    with closing(connection.connect(db_path)) as conn:
        migrate.apply_pending(conn)
    return db_path


def _api_deps(tmp_path: Path) -> ApiDeps:
    return ApiDeps(db_path=_db(tmp_path), scrapers={})


@pytest.fixture
def praha7(tmp_path) -> Profile:
    """An unpaused Praha 7 flat search stored in the database the test's
    deps and client read."""
    with closing(connection.connect(_db(tmp_path))) as conn:
        return stored_profile(conn, name="Praha 7 byty")


def _stub_run_profile(result: ProfileRunResult | None = None, *, error: Exception | None = None):
    """A services.pipeline.run_profile stand-in: records every call and
    returns a canned result (or raises), never touching a scraper."""
    calls = []

    def run_profile(profile, deps, *, dry_run=False, on_scraper_done=None):
        calls.append(profile.id)
        if on_scraper_done is not None:
            on_scraper_done("sreality", ScraperHealth(status="ok", error=None, listing_count=2))
        if error is not None:
            raise error
        return result or ProfileRunResult(
            profile_id=profile.id, run_id="stub-run", started_at=BASE, finished_at=BASE,
            status="ok", scraper_health={"sreality": ScraperHealth(status="ok", error=None, listing_count=2)},
            counts=RunCounts(total=2, new=2, price_drops=0, disappeared=0),
        )

    run_profile.calls = calls
    return run_profile


def _client(tmp_path: Path, *, run_profile=None) -> TestClient:
    app = create_app(TOKEN, _api_deps(tmp_path), run_profile=run_profile or _stub_run_profile())
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

    def test_event_stream_rejects_a_missing_token(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/events")
        assert response.status_code == 401

    def test_event_stream_rejects_a_wrong_query_token(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/events", params={"token": "wrong"})
        assert response.status_code == 401

    def test_event_stream_accepts_a_correct_query_token(self):
        """EventSource cannot set an Authorization header, so /v1/events
        alone also accepts the token as a query parameter. Checked against
        the dependency directly since the TestClient cannot drive a route
        whose body never ends (see the module docstring)."""
        auth = BearerOrQueryTokenAuth(TOKEN)
        auth(authorization=None, token=TOKEN)


class TestCors:
    def test_preflight_from_an_allowed_origin_is_granted(self, tmp_path):
        deps = _api_deps(tmp_path)
        app = create_app(TOKEN, deps, run_profile=_stub_run_profile(),
                         allowed_origins=["http://localhost:5173"])
        client = TestClient(app)
        response = client.options("/v1/profiles", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_preflight_is_refused_without_configured_origins(self, tmp_path):
        """No origins granted means no CORS surface at all: the preflight
        dies on the missing OPTIONS route."""
        client = _client(tmp_path)
        response = client.options("/v1/profiles", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert response.status_code == 405


class TestShutdown:
    def test_calls_the_spawners_callback(self, tmp_path):
        """An authenticated shutdown request is accepted and triggers the
        callback the spawner handed to the app."""
        requested = []
        deps = _api_deps(tmp_path)
        app = create_app(TOKEN, deps, run_profile=_stub_run_profile(),
                         request_shutdown=lambda: requested.append(True))
        response = TestClient(app).post("/v1/shutdown", headers=_auth())
        assert response.status_code == 202
        assert requested == [True]

    def test_requires_the_token(self, tmp_path):
        """Without the bearer token the request is refused and nothing stops."""
        requested = []
        deps = _api_deps(tmp_path)
        app = create_app(TOKEN, deps, run_profile=_stub_run_profile(),
                         request_shutdown=lambda: requested.append(True))
        response = TestClient(app).post("/v1/shutdown")
        assert response.status_code == 401
        assert requested == []

    def test_absent_without_a_callback(self, tmp_path):
        """An app built without a shutdown callback has no shutdown route."""
        client = _client(tmp_path)
        response = client.post("/v1/shutdown", headers=_auth())
        assert response.status_code == 404


class TestListProfiles:
    def test_lists_every_profile_including_paused(self, tmp_path, praha7):
        with closing(connection.connect(_db(tmp_path))) as conn:
            domazlice = stored_profile(
                conn, name="Domazlice domy",
                criteria=criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401)))
            conn.execute("UPDATE profiles SET paused_at = ? WHERE id = ?", (BASE.isoformat(), domazlice.id))
            conn.commit()
        client = _client(tmp_path)
        response = client.get("/v1/profiles", headers=_auth())
        body = response.json()
        assert {p["id"] for p in body} == {praha7.id, domazlice.id}
        paused = next(p for p in body if p["id"] == domazlice.id)
        assert paused["paused_at"] == BASE.isoformat()


def _persist_listing(deps: ApiDeps, profile_id: str, resolved_location: Location | None = None) -> None:
    with deps.open_run_store() as store:
        listing = Listing.build(
            id="sreality:1", source="sreality", title="t", price=20000, location_raw_text="l",
            url="https://example.com/1", resolved_location=resolved_location)
        store.persist_outcome(
            profile_id, DedupOutcome(survivors=[listing], merges=(), uncertain=()),
            {}, current_ids={"sreality:1"})


class TestListListings:
    def test_unknown_profile_is_404(self, tmp_path):
        client = _client(tmp_path)
        response = client.get("/v1/profiles/nope/listings", headers=_auth())
        assert response.status_code == 404

    def test_filter_new_excludes_viewed_listings(self, tmp_path, praha7):
        deps = _api_deps(tmp_path)
        _persist_listing(deps, praha7.id)
        with deps.open_run_store() as store:
            store.mark_viewed(praha7.id, "sreality:1")

        client = _client(tmp_path)

        new_only = client.get(f"/v1/profiles/{praha7.id}/listings", headers=_auth(), params={"filter": "new"})
        assert new_only.json() == []

        every = client.get(f"/v1/profiles/{praha7.id}/listings", headers=_auth(), params={"filter": "all"})
        assert [card["id"] for card in every.json()] == ["sreality:1"]
        assert every.json()[0]["viewed_at"] is not None

    def test_a_listing_carries_its_named_resolved_location(self, tmp_path, praha7):
        deps = _api_deps(tmp_path)
        place = ParsedPlace(names=("Přístavní", "Praha", "Holešovice", "Praha 7"), cislo_popisne="1401")
        with deps.open_gazetteer() as gazetteer:
            _persist_listing(deps, praha7.id, resolved_location=gazetteer.resolve(place))

        client = _client(tmp_path)

        (card,) = client.get(f"/v1/profiles/{praha7.id}/listings", headers=_auth()).json()
        location = card["resolved_location"]
        assert location["kraj"]["name"] == "Hlavní město Praha"
        assert location["okres"] is None
        assert location["obec"]["name"] == "Praha"
        assert location["obvod"]["name"] == "Praha 7"
        assert location["mestska_cast"]["name"] == "Praha 7"
        assert location["cast_obce"]["name"] == "Holešovice"
        assert location["ulice"]["name"] == "Přístavní"
        assert location["cislo_popisne"] == "1401"
        assert location["cislo_orientacni"] is None

    def test_a_listing_whose_text_never_resolved_keeps_only_its_raw_text(self, tmp_path, praha7):
        deps = _api_deps(tmp_path)
        _persist_listing(deps, praha7.id)

        client = _client(tmp_path)

        (card,) = client.get(f"/v1/profiles/{praha7.id}/listings", headers=_auth()).json()
        assert card["resolved_location"] is None
        assert card["location_raw_text"] == "l"


class TestMarkViewed:
    def test_unknown_profile_is_404(self, tmp_path):
        client = _client(tmp_path)
        response = client.patch("/v1/profiles/nope/listings/sreality:1/viewed", headers=_auth())
        assert response.status_code == 404

    def test_marks_the_listing_viewed(self, tmp_path, praha7):
        deps = _api_deps(tmp_path)
        _persist_listing(deps, praha7.id)

        client = _client(tmp_path)

        response = client.patch(f"/v1/profiles/{praha7.id}/listings/sreality:1/viewed", headers=_auth())
        assert response.status_code == 204

        listings = client.get(
            f"/v1/profiles/{praha7.id}/listings", headers=_auth(), params={"filter": "all"}).json()
        assert listings[0]["viewed_at"] is not None


class TestTriggerRun:
    def test_unknown_profile_is_404(self, tmp_path):
        client = _client(tmp_path)
        response = client.post("/v1/runs", headers=_auth(), json={"profile_id": "nope"})
        assert response.status_code == 404

    def test_returns_a_run_id_immediately(self, tmp_path, praha7):
        run_profile = _stub_run_profile()
        client = _client(tmp_path, run_profile=run_profile)
        response = client.post("/v1/runs", headers=_auth(), json={"profile_id": praha7.id})
        assert response.status_code == 202
        body = response.json()
        assert body["profile_id"] == praha7.id
        assert body["run_id"]

    def test_missing_profile_id_is_a_validation_error(self, tmp_path):
        client = _client(tmp_path)
        response = client.post("/v1/runs", headers=_auth(), json={})
        assert response.status_code == 422

    def test_concurrent_requests_never_run_the_pipeline_at_the_same_time(self, tmp_path, praha7):
        overlap_detected = threading.Event()
        currently_running = threading.Event()

        def run_profile(profile, deps, *, dry_run=False, on_scraper_done=None):
            if currently_running.is_set():
                overlap_detected.set()
            currently_running.set()
            time.sleep(0.2)
            currently_running.clear()
            return ProfileRunResult(
                profile_id=profile.id, run_id="r", started_at=BASE, finished_at=BASE,
                status="ok", scraper_health={}, counts=RunCounts(total=0, new=0, price_drops=0, disappeared=0),
            )

        client = _client(tmp_path, run_profile=run_profile)
        responses = [
            client.post("/v1/runs", headers=_auth(), json={"profile_id": praha7.id})
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

    def test_reflects_the_last_run_per_portal(self, tmp_path, praha7):
        run_profile = _stub_run_profile()
        client = _client(tmp_path, run_profile=run_profile)
        client.post("/v1/runs", headers=_auth(), json={"profile_id": praha7.id})

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


def _next_event(gen) -> str:
    """The stream's next real event, skipping keepalive comments."""
    while True:
        item = next(gen)
        if not item.startswith(":"):
            return item


class TestEventStream:
    """The SSE route's generator, driven directly since the TestClient in
    this environment cannot stream a response whose body never ends."""

    def test_published_events_are_yielded_as_sse(self):
        broker = EventBroker()
        gen = iter_sse_events(broker, poll_seconds=0.02)

        def publish():
            time.sleep(0.05)
            broker.publish(RunEvent(kind="run_started", data={"run_id": "r1", "profile_id": "praha7-byty"}))

        threading.Thread(target=publish, daemon=True).start()
        first = _next_event(gen)
        gen.close()

        assert first.startswith("event: run_started\n")
        assert '"run_id": "r1"' in first

    def test_a_quiet_stream_yields_keepalive_comments(self):
        """With no events published, the stream yields an SSE comment every
        poll interval, and closing it there still unsubscribes."""
        broker = EventBroker()
        gen = iter_sse_events(broker, poll_seconds=0.02)

        assert next(gen) == ": keepalive\n\n"
        gen.close()
        assert broker._subscribers == []

    def test_closing_the_generator_unsubscribes_from_the_broker(self):
        broker = EventBroker()
        gen = iter_sse_events(broker, poll_seconds=0.02)

        def publish():
            time.sleep(0.05)
            broker.publish(RunEvent(kind="run_started", data={}))

        threading.Thread(target=publish, daemon=True).start()
        next(gen)  # runs the generator up to and past broker.subscribe()
        gen.close()
        assert broker._subscribers == []

    def test_a_full_run_publishes_started_progress_and_finished(self, tmp_path, praha7):
        run_profile = _stub_run_profile()
        deps = _api_deps(tmp_path)
        app = create_app(TOKEN, deps, run_profile=run_profile)
        broker = app.state.event_broker

        def trigger_shortly_after_subscribing():
            time.sleep(0.1)
            app.state.run_manager.trigger(deps.profile(praha7.id))

        threading.Thread(target=trigger_shortly_after_subscribing, daemon=True).start()

        gen = iter_sse_events(broker, poll_seconds=0.02)
        kinds = []
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and len(kinds) < 3:
            kinds.append(_next_event(gen).split("\n")[0].removeprefix("event: "))
        gen.close()

        assert kinds == ["run_started", "run_progress", "run_finished"]
