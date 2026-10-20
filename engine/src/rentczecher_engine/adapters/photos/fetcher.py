import httpx

from rentczecher_engine.adapters.photos.store import EXTENSIONS
from rentczecher_engine.domain.errors import PhotoFetchError, PhotoGoneError, PhotoRefusedError
from rentczecher_engine.domain.photo import FetchedPhoto

# A portal photo is a few hundred kilobytes, so anything far past that is not one.
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = httpx.Timeout(10, read=20)


class HttpPhotoFetcher:
    """Fetches photos through the app's shared client, so every request
    names the app."""

    def __init__(self, client: httpx.Client):
        self._client = client

    def fetch(self, url: str) -> FetchedPhoto:
        """The photo, or PhotoRefusedError when its server refuses the app,
        PhotoGoneError when the photo is gone or its URL is malformed, and
        PhotoFetchError for any other failure."""
        try:
            with self._client.stream("GET", url, timeout=TIMEOUT) as response:
                if response.status_code in (403, 429):
                    raise PhotoRefusedError(f"{url} answered {response.status_code}")
                if response.status_code in (404, 410):
                    raise PhotoGoneError(f"{url} answered {response.status_code}")
                if response.status_code != 200:
                    raise PhotoFetchError(f"{url} answered {response.status_code}")
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
