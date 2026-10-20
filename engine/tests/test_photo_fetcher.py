"""Tests for fetching photos from image servers.

Run: python3 -m pytest tests/test_photo_fetcher.py -v
"""

import httpx
import pytest

from rentczecher_engine.adapters.photos import fetcher
from rentczecher_engine.adapters.photos.fetcher import HttpPhotoFetcher
from rentczecher_engine.adapters.scrapers.client import IDENTITY_HEADERS, build_client
from rentczecher_engine.domain.errors import PhotoFetchError, PhotoGoneError, PhotoRefusedError

URL = "https://img.example/a.jpg"


def _fetcher(handler):
    requests = []

    def recording(request):
        requests.append(request)
        return handler(request)

    return HttpPhotoFetcher(build_client(transport=httpx.MockTransport(recording))), requests


class TestFetch:
    def test_returns_the_photo_and_its_type(self):
        photos, _ = _fetcher(lambda request: httpx.Response(
            200, content=b"jpeg", headers={"content-type": "image/jpeg; charset=binary"}))
        photo = photos.fetch(URL)
        assert photo.content == b"jpeg"
        assert photo.media_type == "image/jpeg"

    def test_names_the_app(self):
        photos, requests = _fetcher(lambda request: httpx.Response(
            200, content=b"jpeg", headers={"content-type": "image/jpeg"}))
        photos.fetch(URL)
        assert requests[0].headers["User-Agent"] == IDENTITY_HEADERS["User-Agent"]

    @pytest.mark.parametrize("status", [403, 429])
    def test_a_refusal_is_its_own_error(self, status):
        photos, _ = _fetcher(lambda request: httpx.Response(status))
        with pytest.raises(PhotoRefusedError):
            photos.fetch(URL)

    @pytest.mark.parametrize("status", [404, 410])
    def test_a_missing_photo_is_gone(self, status):
        photos, _ = _fetcher(lambda request: httpx.Response(status))
        with pytest.raises(PhotoGoneError):
            photos.fetch(URL)

    def test_a_malformed_url_is_gone(self):
        photos, _ = _fetcher(lambda request: httpx.Response(200))
        with pytest.raises(PhotoGoneError):
            photos.fetch("https://img.example/a\x00.jpg")

    def test_any_other_answer_fails(self):
        photos, _ = _fetcher(lambda request: httpx.Response(500))
        with pytest.raises(PhotoFetchError):
            photos.fetch(URL)

    def test_refuses_what_is_not_a_photo(self):
        photos, _ = _fetcher(lambda request: httpx.Response(
            200, content=b"<html>", headers={"content-type": "text/html"}))
        with pytest.raises(PhotoFetchError):
            photos.fetch(URL)

    def test_refuses_a_file_over_the_size_limit(self, monkeypatch):
        monkeypatch.setattr(fetcher, "MAX_BYTES", 4)
        photos, _ = _fetcher(lambda request: httpx.Response(
            200, content=b"too large", headers={"content-type": "image/jpeg"}))
        with pytest.raises(PhotoFetchError):
            photos.fetch(URL)

    def test_a_connection_failure_fails(self):
        def unreachable(request):
            raise httpx.ConnectError("down")

        photos, _ = _fetcher(unreachable)
        with pytest.raises(PhotoFetchError):
            photos.fetch(URL)
