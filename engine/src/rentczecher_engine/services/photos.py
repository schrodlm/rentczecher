"""Downloading the photos the app wants, and deleting the files nothing
refers to any more."""

import logging
import time
from collections.abc import Callable
from typing import Protocol

from rentczecher_engine.domain.errors import PhotoFetchError, PhotoGoneError, PhotoRefusedError
from rentczecher_engine.domain.photo import FetchedPhoto, PendingPhoto

log = logging.getLogger("rentczecher")

# How many main photos one pass downloads from each portal. The rest wait for
# the next pass.
MAIN_PHOTOS_PER_PORTAL = 100
# The pause between two downloads: shorter for a gallery a user is waiting on.
MAIN_PHOTO_PAUSE_S = 0.5
REQUESTED_PHOTO_PAUSE_S = 0.2
# A file this new may belong to a download another engine process has not
# recorded yet, so the sweep leaves it for a later pass.
SWEEP_GRACE_S = 600


class PhotoRecords(Protocol):
    def requested_photos(self) -> list[PendingPhoto]:
        ...

    def main_photos(self) -> list[PendingPhoto]:
        ...

    def file_keys(self) -> set[str]:
        ...

    def store_photo(self, photo: PendingPhoto, file_key: str) -> bool:
        ...

    def count_failure(self, photo: PendingPhoto, give_up: bool) -> None:
        ...


class PhotoStore(Protocol):
    def put(self, content: bytes, media_type: str) -> str:
        ...

    def delete(self, file_key: str) -> None:
        ...

    def file_keys(self, older_than_s: float) -> set[str]:
        ...

    def remove_partials(self) -> None:
        ...


class PhotoFetcher(Protocol):
    def fetch(self, url: str) -> FetchedPhoto:
        ...


class PhotoDownloader:
    """One pass deletes the files nothing refers to, then downloads every
    photo of the galleries users asked for, then the main photos within each
    portal's budget, one photo at a time. A portal that refuses a photo gets
    no further request in the pass."""

    def __init__(self, records: PhotoRecords, store: PhotoStore, fetcher: PhotoFetcher, *,
                 pause: Callable[[float], None] = time.sleep):
        self._records = records
        self._store = store
        self._fetcher = fetcher
        self._pause = pause

    def run_pass(self, on_property_done: Callable[[str], None] | None = None,
                 should_yield: Callable[[], bool] | None = None) -> None:
        """on_property_done is called with each property whose photos the
        pass finished with, stored or not. The main photos stop early once
        should_yield says another pass is waiting."""
        self._sweep_orphans()
        refused: set[str] = set()
        self._download_all(self._records.requested_photos(), REQUESTED_PHOTO_PAUSE_S, refused,
                           on_property_done, should_yield=None)
        self._download_all(self._within_budget(self._records.main_photos()), MAIN_PHOTO_PAUSE_S, refused,
                           on_property_done, should_yield)

    def _sweep_orphans(self) -> None:
        for file_key in self._store.file_keys(older_than_s=SWEEP_GRACE_S) - self._records.file_keys():
            self._store.delete(file_key)
        self._store.remove_partials()

    def _download_all(self, photos: list[PendingPhoto], pause_s: float, refused: set[str],
                      on_property_done: Callable[[str], None] | None,
                      should_yield: Callable[[], bool] | None) -> None:
        for index, photo in enumerate(photos):
            if should_yield is not None and should_yield():
                return
            if photo.source not in refused:
                self._pause(pause_s)
                if not self._download(photo):
                    refused.add(photo.source)
            is_last_of_property = index + 1 == len(photos) or photos[index + 1].property_id != photo.property_id
            if is_last_of_property and on_property_done is not None:
                on_property_done(photo.property_id)

    def _download(self, photo: PendingPhoto) -> bool:
        """Downloads one photo. False when its portal refused it."""
        try:
            fetched = self._fetcher.fetch(photo.source_url)
        except PhotoRefusedError as error:
            log.warning("photos: %s refused the app, no more photos from it this pass: %s", photo.source, error)
            return False
        except PhotoGoneError as error:
            log.info("photos: %s", error)
            self._records.count_failure(photo, give_up=True)
            return True
        except PhotoFetchError as error:
            log.info("photos: %s", error)
            self._records.count_failure(photo, give_up=False)
            return True
        file_key = self._store.put(fetched.content, fetched.media_type)
        if not self._records.store_photo(photo, file_key):
            self._store.delete(file_key)
        return True

    @staticmethod
    def _within_budget(main_photos: list[PendingPhoto]) -> list[PendingPhoto]:
        taken_by_source: dict[str, int] = {}
        within: list[PendingPhoto] = []
        for photo in main_photos:
            taken = taken_by_source.get(photo.source, 0)
            if taken < MAIN_PHOTOS_PER_PORTAL:
                within.append(photo)
                taken_by_source[photo.source] = taken + 1
        return within
