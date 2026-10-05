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

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_preflight_grants_every_method_a_route_serves(self, tmp_path, method):
        app = create_app(TOKEN, _api_deps(tmp_path), run_profile=_stub_run_profile(),
                         allowed_origins=["http://localhost:5173"])
        response = TestClient(app).options("/v1/profiles", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization",
        })
        assert response.status_code == 200
        assert method in response.headers["access-control-allow-methods"]

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


def _new_profile_body(**overrides) -> dict:
    body = {
        "name": "Praha 7 byty",
        "portals": ["sreality", "remax"],
        "criteria": {
            "offer_type": "rent", "estate_type": "flat", "place": {"kind": "obvod", "code": 78},
            "min_price": None, "max_price": 25000, "min_size_m2": None, "min_land_m2": None,
            "min_rooms": None, "max_rooms": None, "kitchen": None,
        },
        "preferences": _preferences_body(),
    }
    return body | overrides


def _preferences_body(**overrides) -> dict:
    body = {
        "price_per_m2_weight": 0, "disposition_weight": 0, "preferred_dispositions": [],
        "size_weight": 0, "ideal_size_m2": None, "place_weight": 0, "preferred_places": [],
        "land_weight": 0, "ideal_land_m2": None, "price_weight": 0, "max_good_price": None,
    }
    return body | overrides


def _update_body(**overrides) -> dict:
    body = {"name": "Praha 7 byty", "paused": False, "portals": ["sreality"], "preferences": _preferences_body()}
    return body | overrides


class TestGetProfile:
    def test_names_the_places_it_stores_as_codes(self, tmp_path, praha7):
        response = _client(tmp_path).get(f"/v1/profiles/{praha7.id}", headers=_auth())
        assert response.json()["criteria"]["place"] == {
            "kind": "obvod", "code": 78, "name": "Praha 7", "obec": "Praha", "okres": None}

    def test_a_place_the_gazetteer_no_longer_knows_goes_out_unnamed(self, tmp_path):
        with closing(connection.connect(_db(tmp_path))) as conn:
            stored = stored_profile(conn, criteria=criteria(place=PlaceRef("obvod", 999_999_999)))
        response = _client(tmp_path).get(f"/v1/profiles/{stored.id}", headers=_auth())
        assert response.json()["criteria"]["place"] == {
            "kind": "obvod", "code": 999_999_999, "name": None, "obec": None, "okres": None}

    def test_unknown_profile_is_404(self, tmp_path):
        response = _client(tmp_path).get("/v1/profiles/nope", headers=_auth())
        assert response.status_code == 404


class TestCreateProfile:
    def test_a_created_profile_reads_back_as_it_was_answered(self, tmp_path):
        client = _client(tmp_path)
        created = client.post("/v1/profiles", headers=_auth(), json=_new_profile_body())
        assert created.status_code == 201
        assert created.json()["paused_at"] is None
        assert created.json()["portals"] == ["remax", "sreality"]
        assert client.get(f"/v1/profiles/{created.json()['id']}", headers=_auth()).json() == created.json()

    @pytest.mark.parametrize("body", [
        _new_profile_body(criteria=_new_profile_body()["criteria"] | {"place": {"kind": "obvod", "code": 999_999_999}}),
        _new_profile_body(preferences=_preferences_body(
            place_weight=10, preferred_places=[{"kind": "cast_obce", "code": 999_999_999}])),
        _new_profile_body(criteria=_new_profile_body()["criteria"] | {"place": {"kind": "obvod", "code": 2**70}}),
        _new_profile_body(criteria=_new_profile_body()["criteria"] | {"min_price": 30000}),
        _new_profile_body(criteria=_new_profile_body()["criteria"] | {"max_price": 2**70}),
        _new_profile_body(portals=["sreality", "sreality"]),
        _new_profile_body(portals=["idnes"]),
        _new_profile_body(preferences=_preferences_body(preferred_dispositions=["2+2"])),
        _new_profile_body(colour="blue"),
    ], ids=["unknown place", "unknown preferred place", "place code too large to store", "min above max", "price too large to store",
            "repeated portal", "unknown portal", "unknown disposition", "unknown field"])
    def test_an_invalid_profile_is_422_and_stores_nothing(self, tmp_path, body):
        client = _client(tmp_path)
        response = client.post("/v1/profiles", headers=_auth(), json=body)
        assert response.status_code == 422
        assert client.get("/v1/profiles", headers=_auth()).json() == []


class TestUpdateProfile:
    def test_everything_but_the_criteria_changes(self, tmp_path, praha7):
        client = _client(tmp_path)
        body = _update_body(name="Byty", portals=["bezrealitky"], preferences=_preferences_body(
            place_weight=10, preferred_places=[{"kind": "cast_obce", "code": 490067}]))
        response = client.put(f"/v1/profiles/{praha7.id}", headers=_auth(), json=body)
        assert response.status_code == 200
        updated = client.get(f"/v1/profiles/{praha7.id}", headers=_auth()).json()
        assert (updated["name"], updated["portals"]) == ("Byty", ["bezrealitky"])
        assert [place["name"] for place in updated["preferences"]["preferred_places"]] == ["Holešovice"]
        assert updated["criteria"]["place"]["code"] == 78

    def test_pausing_stamps_the_time_and_resuming_clears_it(self, tmp_path, praha7):
        client = _client(tmp_path)
        paused = client.put(f"/v1/profiles/{praha7.id}", headers=_auth(), json=_update_body(paused=True))
        assert paused.json()["paused_at"] is not None
        resumed = client.put(f"/v1/profiles/{praha7.id}", headers=_auth(), json=_update_body(paused=False))
        assert resumed.json()["paused_at"] is None

    @pytest.mark.parametrize("body", [
        _update_body(criteria=_new_profile_body()["criteria"]),
        _update_body(preferences=_preferences_body(
            place_weight=10, preferred_places=[{"kind": "cast_obce", "code": 999_999_999}])),
        _update_body(preferences=_preferences_body(size_weight=10)),
        _update_body(preferences=_preferences_body(ideal_size_m2=2**70)),
    ], ids=["criteria", "unknown preferred place", "weight without its setting", "size too large to store"])
    def test_an_invalid_update_is_422_and_changes_nothing(self, tmp_path, praha7, body):
        client = _client(tmp_path)
        before = client.get(f"/v1/profiles/{praha7.id}", headers=_auth()).json()
        response = client.put(f"/v1/profiles/{praha7.id}", headers=_auth(), json=body | {"name": "Changed"})
        assert response.status_code == 422
        assert client.get(f"/v1/profiles/{praha7.id}", headers=_auth()).json() == before

    def test_unknown_profile_is_404(self, tmp_path):
        response = _client(tmp_path).put("/v1/profiles/nope", headers=_auth(), json=_update_body())
        assert response.status_code == 404


class TestDeleteProfile:
    def test_a_deleted_profile_is_gone(self, tmp_path, praha7):
        client = _client(tmp_path)
        assert client.delete(f"/v1/profiles/{praha7.id}", headers=_auth()).status_code == 204
        assert client.get(f"/v1/profiles/{praha7.id}", headers=_auth()).status_code == 404

    def test_unknown_profile_is_404(self, tmp_path):
        response = _client(tmp_path).delete("/v1/profiles/nope", headers=_auth())
        assert response.status_code == 404


class TestSearchPlaces:
    def test_finds_places_by_the_start_of_their_name_with_their_obec_and_okres(self, tmp_path):
        response = _client(tmp_path).get("/v1/places", headers=_auth(), params={"q": "holešovice", "kind": "cast_obce"})
        assert response.json() == [
            {"kind": "cast_obce", "code": 490067, "name": "Holešovice", "obec": "Praha", "okres": None},
            {"kind": "cast_obce", "code": 41114, "name": "Holešovice", "obec": "Chroustovice", "okres": "Chrudim"},
        ]

    def test_within_keeps_places_at_least_partly_inside_it(self, tmp_path):
        response = _client(tmp_path).get("/v1/places", headers=_auth(), params={"q": "holeš", "within": "obvod:78"})
        assert [(place["kind"], place["name"]) for place in response.json()] == [("cast_obce", "Holešovice")]

    def test_kinds_narrow_the_results(self, tmp_path):
        params = {"q": "domaž", "kind": ["okres", "obec"]}
        response = _client(tmp_path).get("/v1/places", headers=_auth(), params=params)
        assert {place["kind"] for place in response.json()} == {"okres", "obec"}

    @pytest.mark.parametrize("params", [
        {},
        {"q": "na", "within": "obvod:999999999"},
        {"q": "na", "within": "obvod"},
        {"q": "na", "within": "nope:1"},
        {"q": "na", "within": f"obvod:{2**70}"},
        {"q": "na", "kind": "nope"},
    ], ids=["no query", "unknown within", "within without code", "within of no kind",
            "within code too large to store", "unknown kind"])
    def test_an_invalid_search_is_422(self, tmp_path, params):
        response = _client(tmp_path).get("/v1/places", headers=_auth(), params=params)
        assert response.status_code == 422


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
