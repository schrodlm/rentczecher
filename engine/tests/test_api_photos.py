"""Tests for serving stored photos through signed links.

Run: python3 -m pytest tests/test_api_photos.py -v
"""

from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

from rentczecher_engine.adapters.api.app import create_app
from rentczecher_engine.adapters.api.deps import ApiDeps
from rentczecher_engine.adapters.api.photo_links import PhotoLinks
from rentczecher_engine.adapters.photos.store import FilePhotoStore
from rentczecher_engine.adapters.repositories.sqlite import connection, migrate

TOKEN = "test-token"
FILE_KEY = "a" * 32 + ".jpg"


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "t.db"
    with closing(connection.connect(db_path)) as conn:
        migrate.apply_pending(conn)
    deps = ApiDeps(db_path=db_path, photos_dir=tmp_path / "photos", scrapers={})
    return TestClient(create_app(TOKEN, deps))


def _stored(tmp_path: Path) -> str:
    return FilePhotoStore(tmp_path / "photos").put(b"jpeg bytes", "image/jpeg")


def _signature(links: PhotoLinks, file_key: str) -> str:
    return links.link(file_key).split("?sig=")[1]


class TestPhotoLinks:
    def test_a_link_carries_a_valid_signature(self):
        links = PhotoLinks(b"secret")
        assert links.is_valid(FILE_KEY, _signature(links, FILE_KEY))

    def test_a_signature_fits_only_its_own_photo(self):
        links = PhotoLinks(b"secret")
        assert not links.is_valid("b" * 32 + ".jpg", _signature(links, FILE_KEY))

    def test_a_link_from_another_run_is_invalid(self):
        assert not PhotoLinks(b"this run").is_valid(FILE_KEY, _signature(PhotoLinks(b"earlier run"), FILE_KEY))


class TestPhotoRoute:
    def test_serves_the_photo_for_a_signed_link(self, tmp_path):
        client = _client(tmp_path)
        file_key = _stored(tmp_path)
        response = client.get(client.app.state.photo_links.link(file_key))
        assert response.status_code == 200
        assert response.content == b"jpeg bytes"
        assert response.headers["content-type"] == "image/jpeg"
        assert "immutable" in response.headers["cache-control"]

    def test_refuses_a_link_without_a_signature(self, tmp_path):
        client = _client(tmp_path)
        file_key = _stored(tmp_path)
        assert client.get(f"/v1/photos/{file_key}").status_code == 403

    def test_refuses_a_wrong_signature(self, tmp_path):
        client = _client(tmp_path)
        file_key = _stored(tmp_path)
        assert client.get(f"/v1/photos/{file_key}?sig=forged").status_code == 403

    def test_the_api_token_does_not_open_a_photo(self, tmp_path):
        client = _client(tmp_path)
        file_key = _stored(tmp_path)
        response = client.get(f"/v1/photos/{file_key}", headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 403

    def test_a_photo_no_longer_stored_is_not_found(self, tmp_path):
        client = _client(tmp_path)
        file_key = _stored(tmp_path)
        FilePhotoStore(tmp_path / "photos").delete(file_key)
        assert client.get(client.app.state.photo_links.link(file_key)).status_code == 404

    def test_a_signed_key_that_is_no_photo_key_is_not_found(self, tmp_path):
        client = _client(tmp_path)
        assert client.get(client.app.state.photo_links.link("..%2Fsecrets")).status_code == 404
