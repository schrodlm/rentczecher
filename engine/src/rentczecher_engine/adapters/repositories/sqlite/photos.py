import sqlite3

from rentczecher_engine.domain.photo import (
    GALLERY_LIMIT,
    MAX_ATTEMPTS,
    Gallery,
    PendingAdvertPage,
    PendingPhoto,
    gallery_status,
)

# Each property's gallery listing: the one of its listings with the most
# photos, the lowest id among equals.
_GALLERY_LISTINGS = """
    WITH photo_counts AS (
        SELECT listings.property_id AS property_id, listings.id AS listing_id,
               count(listing_photos.position) AS photo_count
        FROM listings
        LEFT JOIN listing_photos ON listing_photos.listing_id = listings.id
        GROUP BY listings.id
    ),
    gallery_listings AS (
        SELECT property_id, listing_id FROM (
            SELECT property_id, listing_id,
                   row_number() OVER (PARTITION BY property_id ORDER BY photo_count DESC, listing_id) AS rank
            FROM photo_counts
        )
        WHERE rank = 1
    )
"""


class SqlitePhotoRepository:
    """Each listing's gallery: the portal's URL of every photo in order, and
    the stored file once it is downloaded. Write methods never commit."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def _to_pending(self, row: sqlite3.Row) -> PendingPhoto:
        return PendingPhoto(
            property_id=row["property_id"],
            listing_id=row["listing_id"],
            position=row["position"],
            source_url=row["source_url"],
            source=row["source"],
        )

    def _to_pending_advert_page(self, row: sqlite3.Row) -> PendingAdvertPage:
        return PendingAdvertPage(
            property_id=row["property_id"],
            listing_id=row["listing_id"],
            source=row["source"],
            url=row["url"],
        )

    def record_gallery(self, listing_id: str, photo_urls: tuple[str, ...], *, on_advert_page: bool = False) -> None:
        """Records a listing's gallery the first time a scan sees it. A
        gallery already recorded stays as it is."""
        if on_advert_page:
            stmt = "INSERT INTO advert_page_reads (listing_id) VALUES (?) ON CONFLICT (listing_id) DO NOTHING"
            self._conn.execute(stmt, (listing_id,))
        stmt = "SELECT 1 FROM listing_photos WHERE listing_id = ? LIMIT 1"
        if self._conn.execute(stmt, (listing_id,)).fetchone() is not None:
            return
        stmt = "INSERT INTO listing_photos (listing_id, position, source_url) VALUES (?, ?, ?)"
        for position, source_url in enumerate(photo_urls[:GALLERY_LIMIT]):
            self._conn.execute(stmt, (listing_id, position, source_url))

    def request_gallery(self, profile_id: str, property_id: str, requested_at: str) -> bool:
        """Asks for the property's whole gallery. False when the profile does
        not track the property. A request already made keeps its time."""
        if not self._tracks(profile_id, property_id):
            return False
        stmt = """
            INSERT INTO gallery_requests (property_id, requested_at) VALUES (?, ?)
            ON CONFLICT (property_id) DO NOTHING
        """
        self._conn.execute(stmt, (property_id, requested_at))
        return True

    def requested_advert_pages(self) -> list[PendingAdvertPage]:
        """The unread advert page of every requested gallery that only its
        advert's page lists in whole, the latest request first."""
        stmt = _GALLERY_LISTINGS + """
            SELECT listings.property_id AS property_id, listings.id AS listing_id,
                   listings.source AS source, listings.url AS url
            FROM gallery_listings
            JOIN listings ON listings.id = gallery_listings.listing_id
            JOIN gallery_requests ON gallery_requests.property_id = listings.property_id
            JOIN advert_page_reads ON advert_page_reads.listing_id = listings.id
            WHERE advert_page_reads.read_at IS NULL AND advert_page_reads.attempts < ?
            ORDER BY gallery_requests.requested_at DESC, listings.id
        """
        rows = self._conn.execute(stmt, (MAX_ATTEMPTS,))
        return [self._to_pending_advert_page(row) for row in rows]

    def record_advert_gallery(self, listing_id: str, photo_urls: tuple[str, ...], read_at: str) -> None:
        """Replaces the listing's gallery with the one its advert page lists.
        A photo the page lists again keeps its stored file and its attempts,
        and a page listing none leaves the search's photos in place. A listing
        deleted while its page was read is left alone."""
        stmt = "UPDATE advert_page_reads SET read_at = ? WHERE listing_id = ?"
        if self._conn.execute(stmt, (read_at, listing_id)).rowcount == 0 or not photo_urls:
            return
        stmt = "SELECT source_url, file_key, attempts FROM listing_photos WHERE listing_id = ?"
        previous_by_url = {row["source_url"]: row for row in self._conn.execute(stmt, (listing_id,)).fetchall()}
        stmt = "DELETE FROM listing_photos WHERE listing_id = ?"
        self._conn.execute(stmt, (listing_id,))
        stmt = """
            INSERT INTO listing_photos (listing_id, position, source_url, file_key, attempts)
            VALUES (?, ?, ?, ?, ?)
        """
        for position, source_url in enumerate(photo_urls[:GALLERY_LIMIT]):
            previous = previous_by_url.pop(source_url, None)
            file_key = previous["file_key"] if previous is not None else None
            attempts = previous["attempts"] if previous is not None else 0
            self._conn.execute(stmt, (listing_id, position, source_url, file_key, attempts))

    def count_advert_failure(self, listing_id: str, give_up: bool) -> None:
        """Counts a failed read of the advert page, or gives the page up at
        once, the listing keeping the photos its search result gave."""
        if give_up:
            stmt = "UPDATE advert_page_reads SET attempts = ? WHERE listing_id = ?"
            self._conn.execute(stmt, (MAX_ATTEMPTS, listing_id))
        else:
            stmt = "UPDATE advert_page_reads SET attempts = attempts + 1 WHERE listing_id = ?"
            self._conn.execute(stmt, (listing_id,))

    def requested_photos(self) -> list[PendingPhoto]:
        """The unstored photos of every requested gallery, the latest request
        first."""
        stmt = _GALLERY_LISTINGS + """
            SELECT listings.property_id AS property_id, listing_photos.listing_id AS listing_id,
                   listing_photos.position AS position, listing_photos.source_url AS source_url,
                   listings.source AS source
            FROM listing_photos
            JOIN listings ON listings.id = listing_photos.listing_id
            JOIN gallery_listings ON gallery_listings.listing_id = listing_photos.listing_id
            JOIN gallery_requests ON gallery_requests.property_id = listings.property_id
            WHERE listing_photos.file_key IS NULL AND listing_photos.attempts < ?
            ORDER BY gallery_requests.requested_at DESC, listing_photos.listing_id, listing_photos.position
        """
        rows = self._conn.execute(stmt, (MAX_ATTEMPTS,))
        return [self._to_pending(row) for row in rows]

    def main_photos(self) -> list[PendingPhoto]:
        """The unstored main photo of every property no one asked the whole
        gallery for, the property first seen last first."""
        stmt = _GALLERY_LISTINGS + """
            SELECT listings.property_id AS property_id, listing_photos.listing_id AS listing_id,
                   listing_photos.position AS position, listing_photos.source_url AS source_url,
                   listings.source AS source
            FROM listing_photos
            JOIN listings ON listings.id = listing_photos.listing_id
            JOIN gallery_listings ON gallery_listings.listing_id = listing_photos.listing_id
            WHERE listing_photos.position = 0
              AND listing_photos.file_key IS NULL AND listing_photos.attempts < ?
              AND listings.property_id NOT IN (SELECT property_id FROM gallery_requests)
            ORDER BY (
                SELECT min(first_seen_at) FROM listing_tracking WHERE listing_id = listings.id
            ) DESC, listing_photos.listing_id
        """
        rows = self._conn.execute(stmt, (MAX_ATTEMPTS,))
        return [self._to_pending(row) for row in rows]

    def store_photo(self, listing_id: str, position: int, source_url: str, file_key: str) -> bool:
        """Records the photo's stored file. False when the photo is no longer
        there to record, its listing deleted in the meantime."""
        stmt = """
            UPDATE listing_photos SET file_key = ?
            WHERE listing_id = ? AND position = ? AND source_url = ? AND file_key IS NULL
        """
        return self._conn.execute(stmt, (file_key, listing_id, position, source_url)).rowcount == 1

    def count_failure(self, listing_id: str, position: int, give_up: bool) -> None:
        """Counts a failed download, or gives the photo up at once."""
        if give_up:
            stmt = "UPDATE listing_photos SET attempts = ? WHERE listing_id = ? AND position = ?"
            self._conn.execute(stmt, (MAX_ATTEMPTS, listing_id, position))
        else:
            stmt = "UPDATE listing_photos SET attempts = attempts + 1 WHERE listing_id = ? AND position = ?"
            self._conn.execute(stmt, (listing_id, position))

    def file_keys(self) -> set[str]:
        stmt = "SELECT file_key FROM listing_photos WHERE file_key IS NOT NULL"
        return {row["file_key"] for row in self._conn.execute(stmt)}

    def main_photo_keys(self, profile_id: str) -> dict[str, str]:
        """The stored main photo of each property the profile tracks, by
        property id."""
        stmt = _GALLERY_LISTINGS + """
            SELECT gallery_listings.property_id AS property_id, listing_photos.file_key AS file_key
            FROM gallery_listings
            JOIN property_tracking ON property_tracking.property_id = gallery_listings.property_id
            JOIN listing_photos ON listing_photos.listing_id = gallery_listings.listing_id
            WHERE property_tracking.profile_id = ?
              AND listing_photos.position = 0 AND listing_photos.file_key IS NOT NULL
        """
        return {row["property_id"]: row["file_key"] for row in self._conn.execute(stmt, (profile_id,))}

    def gallery(self, profile_id: str, property_id: str) -> Gallery | None:
        """The property's gallery, or None when the profile does not track
        the property."""
        if not self._tracks(profile_id, property_id):
            return None
        stmt = _GALLERY_LISTINGS + """
            SELECT listings.id AS listing_id, listings.source AS source, listings.url AS url,
                   EXISTS (SELECT 1 FROM gallery_requests WHERE property_id = listings.property_id) AS requested,
                   EXISTS (
                       SELECT 1 FROM advert_page_reads
                       WHERE listing_id = listings.id AND read_at IS NULL AND attempts < ?
                   ) AS advert_page_unread
            FROM gallery_listings
            JOIN listings ON listings.id = gallery_listings.listing_id
            WHERE gallery_listings.property_id = ?
        """
        listing = self._conn.execute(stmt, (MAX_ATTEMPTS, property_id)).fetchone()
        if listing is None:
            return None
        stmt = """
            SELECT position, file_key, attempts FROM listing_photos
            WHERE listing_id = ? ORDER BY position
        """
        photos = self._conn.execute(stmt, (listing["listing_id"],)).fetchall()
        file_keys = tuple(photo["file_key"] for photo in photos if photo["file_key"] is not None)
        pending = sum(
            1 for photo in photos
            if photo["file_key"] is None and photo["attempts"] < MAX_ATTEMPTS
            and (listing["requested"] or photo["position"] == 0)
        )
        return Gallery(
            source=listing["source"],
            url=listing["url"],
            photo_count=len(photos),
            file_keys=file_keys,
            status=gallery_status(len(photos), len(file_keys), pending,
                                  reading_advert_page=bool(listing["requested"] and listing["advert_page_unread"])),
        )

    def _tracks(self, profile_id: str, property_id: str) -> bool:
        stmt = "SELECT 1 FROM property_tracking WHERE profile_id = ? AND property_id = ?"
        return self._conn.execute(stmt, (profile_id, property_id)).fetchone() is not None
