import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta

from rentczecher.adapters.repositories.repositories import DisappearedListing, ListingRepository
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.price import PriceObservation


class SqliteListingRepository(ListingRepository):
    def __init__(self, conn: sqlite3.Connection, *, now: Callable[[], datetime] = utc_now):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row  # column-name indexing on rows
        self._now = now

    def _to_observation(self, row: sqlite3.Row) -> PriceObservation:
        return PriceObservation(
            listing_id=row["listing_id"],
            price=row["price"],
            charges=row["charges"],
            observed_at=row["observed_at"],
            observed_in_run_id=row["observed_in_run_id"],
        )

    def _to_disappeared_listing(self, row: sqlite3.Row) -> DisappearedListing:
        return DisappearedListing(
            id=row["id"],
            source=row["source"],
            url=row["url"],
            first_seen_at=row["first_seen_at"],
            miss_count=row["miss_count"],
            title=row["title"],
            location=row["location"],
            price=row["price"],
        )

    def seen_ids(self, profile_id: str) -> set[str]:
        stmt = "SELECT id FROM listings WHERE profile_id = ?"
        return {row["id"] for row in self._conn.execute(stmt, (profile_id,))}

    def upsert(self, profile_id: str, property_id: str, listing: Listing) -> None:
        now = self._now().isoformat()
        scraped_at = listing.scraped_at or now
        existing = self._conn.execute(
            "SELECT id FROM listings WHERE id = ?", (listing.id,)).fetchone()
        if existing is None:
            insert = """
                INSERT INTO listings (
                    id, property_id, profile_id, source, active, url,
                    first_seen_at, last_seen_at, scraped_at, miss_count
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, 0)
            """
            self._conn.execute(insert, (
                listing.id, property_id, profile_id, listing.source, listing.url,
                now, now, scraped_at,
            ))
        else:
            update = """
                UPDATE listings SET last_seen_at = ?, scraped_at = ?, active = 1, miss_count = 0
                WHERE id = ?
            """
            self._conn.execute(update, (now, scraped_at, listing.id))
        self.record_price_observation(PriceObservation(
            listing_id=listing.id, price=listing.price,
            charges=listing.charges, observed_at=now))
        self._conn.commit()

    def record_price_observation(self, observation: PriceObservation) -> None:
        stmt = """
            INSERT INTO price_observations (
                listing_id, price, charges, observed_at, observed_in_run_id
            ) VALUES (?, ?, ?, ?, ?)
        """
        self._conn.execute(stmt, (
            observation.listing_id, observation.price, observation.charges,
            observation.observed_at, observation.observed_in_run_id,
        ))
        self._conn.commit()

    def price_history(self, listing_id: str) -> list[PriceObservation]:
        stmt = """
            SELECT listing_id, price, charges, observed_at, observed_in_run_id
            FROM price_observations WHERE listing_id = ? ORDER BY observed_at
        """
        rows = self._conn.execute(stmt, (listing_id,))
        return [self._to_observation(row) for row in rows]

    def increment_miss_counts(self, profile_id: str, current_ids: set[str]) -> None:
        stmt = "SELECT id, miss_count FROM listings WHERE profile_id = ?"
        rows = self._conn.execute(stmt, (profile_id,)).fetchall()
        for row in rows:
            if row["id"] in current_ids:
                if row["miss_count"] > 0:
                    self._conn.execute(
                        "UPDATE listings SET miss_count = 0, active = 1 WHERE id = ?",
                        (row["id"],))
            else:
                self._conn.execute(
                    "UPDATE listings SET miss_count = miss_count + 1, active = 0 WHERE id = ?",
                    (row["id"],))
        self._conn.commit()

    def get_disappeared(self, profile_id: str, current_ids: set[str],
                        max_age_days: int = 7, min_misses: int = 3) -> list[DisappearedListing]:
        cutoff = (self._now() - timedelta(days=max_age_days)).isoformat()
        # Reported only while recently first seen: an old listing that finally
        # drops off is stale, not news.
        # Latest price observation per listing: highest id wins ties on
        # observed_at, since id is monotonic insertion order and observed_at
        # is not guaranteed distinct.
        stmt = """
            SELECT listings.id AS id, listings.source AS source, listings.url AS url,
                   listings.first_seen_at AS first_seen_at, listings.miss_count AS miss_count,
                   properties.title AS title, properties.location AS location,
                   latest_price.price AS price
            FROM listings
            JOIN properties ON properties.id = listings.property_id
            LEFT JOIN price_observations AS latest_price
                ON latest_price.id = (
                    SELECT id FROM price_observations
                    WHERE listing_id = listings.id
                    ORDER BY observed_at DESC, id DESC
                    LIMIT 1
                )
            WHERE listings.profile_id = ? AND listings.miss_count >= ?
                  AND listings.first_seen_at >= ?
        """
        rows = self._conn.execute(stmt, (profile_id, min_misses, cutoff))
        return [
            self._to_disappeared_listing(row)
            for row in rows
            if row["id"] not in current_ids
        ]

    def prune(self, profile_id: str, max_age_days: int = 90) -> int:
        cutoff = (self._now() - timedelta(days=max_age_days)).isoformat()
        stmt = "DELETE FROM listings WHERE profile_id = ? AND last_seen_at < ?"
        cursor = self._conn.execute(stmt, (profile_id, cutoff))
        self._conn.commit()
        return cursor.rowcount
