import sqlite3
from collections.abc import Callable
from datetime import datetime

from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.adapters.repositories.sqlite.photos import SqlitePhotoRepository
from rentczecher_engine.domain.photo import PendingAdvertPage, PendingPhoto


class SqlitePhotoRecords:
    """The photo downloader's view of the database, each write its own unit
    of work, so a photo stored is recorded even if a later one fails."""

    def __init__(self, conn: sqlite3.Connection, *, now: Callable[[], datetime] = utc_now):
        self._conn = conn
        self._photos = SqlitePhotoRepository(conn)
        self._now = now

    def requested_advert_pages(self) -> list[PendingAdvertPage]:
        return self._photos.requested_advert_pages()

    def record_advert_gallery(self, page: PendingAdvertPage, photo_urls: tuple[str, ...]) -> None:
        try:
            self._photos.record_advert_gallery(page.listing_id, photo_urls, self._now().isoformat())
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def count_advert_failure(self, page: PendingAdvertPage, give_up: bool) -> None:
        try:
            self._photos.count_advert_failure(page.listing_id, give_up)
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def requested_photos(self) -> list[PendingPhoto]:
        return self._photos.requested_photos()

    def main_photos(self) -> list[PendingPhoto]:
        return self._photos.main_photos()

    def file_keys(self) -> set[str]:
        return self._photos.file_keys()

    def store_photo(self, photo: PendingPhoto, file_key: str) -> bool:
        try:
            stored = self._photos.store_photo(photo.listing_id, photo.position, photo.source_url, file_key)
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        return stored

    def count_failure(self, photo: PendingPhoto, give_up: bool) -> None:
        try:
            self._photos.count_failure(photo.listing_id, photo.position, give_up)
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
