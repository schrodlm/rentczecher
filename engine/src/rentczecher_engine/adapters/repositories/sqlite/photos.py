import sqlite3

from rentczecher_engine.domain.photo import GALLERY_LIMIT


class SqlitePhotoRepository:
    """Each listing's gallery: the portal's URL of every photo in order, and
    the stored file once it is downloaded."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def record_gallery(self, listing_id: str, photo_urls: tuple[str, ...]) -> None:
        """Records a listing's gallery the first time a scan sees it, without
        committing. A gallery already recorded stays as it is."""
        stmt = "SELECT 1 FROM listing_photos WHERE listing_id = ? LIMIT 1"
        if self._conn.execute(stmt, (listing_id,)).fetchone() is not None:
            return
        stmt = "INSERT INTO listing_photos (listing_id, position, source_url) VALUES (?, ?, ?)"
        for position, source_url in enumerate(photo_urls[:GALLERY_LIMIT]):
            self._conn.execute(stmt, (listing_id, position, source_url))
