import httpx

from rentczecher_engine.adapters.photos.store import EXTENSIONS
from rentczecher_engine.domain.errors import PhotoFetchError, PhotoGoneError, PhotoRefusedError
from rentczecher_engine.domain.photo import FetchedPhoto

# A full-size upload some portals serve runs to a few megabytes, so anything
# past this is not a photo.
MAX_BYTES = 10 * 1024 * 1024
# An advert page is a few hundred kilobytes.
MAX_PAGE_BYTES = 2 * 1024 * 1024
TIMEOUT = httpx.Timeout(10, read=20)


def _raise_for_status(url: str, status_code: int) -> None:
    if status_code in (403, 429):
        raise PhotoRefusedError(f"{url} answered {status_code}")
    if status_code in (404, 410):
        raise PhotoGoneError(f"{url} answered {status_code}")
    if status_code != 200:
        raise PhotoFetchError(f"{url} answered {status_code}")


class HttpPhotoFetcher:
    """Fetches photos through the app's shared client, so every request
    names the app."""

    def __init__(self, client: httpx.Client):
        self._client = client

    def fetch(self, url: str) -> FetchedPhoto:
        """Raises PhotoRefusedError, PhotoGoneError or PhotoFetchError."""
        try:
            with self._client.stream("GET", url, timeout=TIMEOUT) as response:
                _raise_for_status(url, response.status_code)
                media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if media_type not in EXTENSIONS:
                    raise PhotoFetchError(f"{url} is {media_type or 'untyped'}, not a photo")
                content = bytearray()
                for chunk in response.iter_bytes():
                    content += chunk
                    if len(content) > MAX_BYTES:
                        raise PhotoFetchError(f"{url} is larger than {MAX_BYTES} bytes")
        except httpx.InvalidURL as error:
            raise PhotoGoneError(f"{url}: {error}") from error
        except httpx.HTTPError as error:
            raise PhotoFetchError(f"{url}: {error}") from error
        return FetchedPhoto(content=bytes(content), media_type=media_type)


class HttpAdvertPageFetcher:
    """Fetches advert pages through the app's shared client, under the same
    rules as photos."""

    def __init__(self, client: httpx.Client):
        self._client = client

    def fetch(self, url: str) -> str:
        """Raises PhotoRefusedError, PhotoGoneError or PhotoFetchError."""
        try:
            with self._client.stream("GET", url, timeout=TIMEOUT) as response:
                _raise_for_status(url, response.status_code)
                content = bytearray()
                for chunk in response.iter_bytes():
                    content += chunk
                    if len(content) > MAX_PAGE_BYTES:
                        raise PhotoFetchError(f"{url} is larger than {MAX_PAGE_BYTES} bytes")
                encoding = response.encoding or "utf-8"
        except httpx.InvalidURL as error:
            raise PhotoGoneError(f"{url}: {error}") from error
        except httpx.HTTPError as error:
            raise PhotoFetchError(f"{url}: {error}") from error
        return bytes(content).decode(encoding, errors="replace")
