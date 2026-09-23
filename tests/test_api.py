"""Tests for the sidecar API: auth and the routes over a real SQLite
database, driven through FastAPI's TestClient.

Run: python3 -m pytest tests/test_api.py -v
"""

from pathlib import Path

from fastapi.testclient import TestClient

from rentczecher.adapters.api.app import create_app
from rentczecher.adapters.api.deps import ApiDeps
from rentczecher.adapters.repositories.sqlite import connection, migrate

TOKEN = "test-token"

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


def _client(tmp_path: Path, *, profiles: dict | None = None) -> TestClient:
    deps = _api_deps(tmp_path, profiles)
    app = create_app(TOKEN, deps)
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
