import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta

from rentczecher.adapters.repositories.repositories import ListingRepository
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.listing import DisappearedListing
from rentczecher.domain.price import PriceObservation


class SqliteListingRepository(ListingRepository):
    """A listing row is a fact of the portal posting, shared by every
    profile that sees it. Which profile has seen it, when, and how many
    scrapes have missed it lives in listing_tracking, one row per profile
    and listing."""

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
        stmt = "SELECT listing_id FROM listing_tracking WHERE profile_id = ?"
        return {row["listing_id"] for row in self._conn.execute(stmt, (profile_id,))}

    def upsert(self, profile_id: str, property_id: str, listing: Listing) -> None:
        now = self._now().isoformat()
        scraped_at = listing.scraped_at or now
        fact = self._conn.execute(
            "SELECT id FROM listings WHERE id = ?", (listing.id,)).fetchone()
        if fact is None:
            insert = """
                INSERT INTO listings (id, property_id, source, url, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            """
            self._conn.execute(insert, (
                listing.id, property_id, listing.source, listing.url, scraped_at,
            ))
        else:
            update = "UPDATE listings SET property_id = ?, scraped_at = ? WHERE id = ?"
            self._conn.execute(update, (property_id, scraped_at, listing.id))
        tracked = self._conn.execute(
            "SELECT listing_id FROM listing_tracking WHERE profile_id = ? AND listing_id = ?",
            (profile_id, listing.id)).fetchone()
        if tracked is None:
            insert = """
                INSERT INTO listing_tracking (
                    profile_id, listing_id, first_seen_at, last_seen_at, miss_count
                ) VALUES (?, ?, ?, ?, 0)
            """
            self._conn.execute(insert, (profile_id, listing.id, now, now))
        else:
            update = """
                UPDATE listing_tracking SET last_seen_at = ?, miss_count = 0
                WHERE profile_id = ? AND listing_id = ?
            """
            self._conn.execute(update, (now, profile_id, listing.id))
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

    def latest_prices(self, profile_id: str) -> dict[str, int]:
        """The most recent observed price per listing the profile tracks.

        A listing with no price observation yet is absent from the result,
        so it can never register as a price drop.
        """
        # Latest price observation per listing: highest id wins ties on
        # observed_at, since id is monotonic insertion order and observed_at
        # is not guaranteed distinct.
        stmt = """
            SELECT listing_tracking.listing_id AS id, latest_price.price AS price
            FROM listing_tracking
            JOIN price_observations AS latest_price
                ON latest_price.id = (
                    SELECT id FROM price_observations
                    WHERE listing_id = listing_tracking.listing_id
                    ORDER BY observed_at DESC, id DESC
                    LIMIT 1
                )
            WHERE listing_tracking.profile_id = ?
        """
        rows = self._conn.execute(stmt, (profile_id,))
        return {row["id"]: row["price"] for row in rows}

    def property_id_of(self, listing_id: str) -> str | None:
        stmt = "SELECT property_id FROM listings WHERE id = ?"
        row = self._conn.execute(stmt, (listing_id,)).fetchone()
        return row["property_id"] if row else None

    def increment_miss_counts(self, profile_id: str, current_ids: set[str]) -> None:
        stmt = "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?"
        rows = self._conn.execute(stmt, (profile_id,)).fetchall()
        for row in rows:
            if row["listing_id"] in current_ids:
                if row["miss_count"] > 0:
                    self._conn.execute(
                        "UPDATE listing_tracking SET miss_count = 0 "
                        "WHERE profile_id = ? AND listing_id = ?",
                        (profile_id, row["listing_id"]))
            else:
                self._conn.execute(
                    "UPDATE listing_tracking SET miss_count = miss_count + 1 "
                    "WHERE profile_id = ? AND listing_id = ?",
                    (profile_id, row["listing_id"]))
        self._conn.commit()

    def get_disappeared(self, profile_id: str, current_ids: set[str],
                        max_age_days: int = 7, min_misses: int = 3) -> list[DisappearedListing]:
        candidates = self._tracked_within_window(profile_id, max_age_days)
        return [
            self._to_disappeared_listing(row)
            for row in candidates
            if row["id"] not in current_ids and row["miss_count"] >= min_misses
        ]

    def pending_disappeared(self, profile_id: str, current_ids: set[str],
                            max_age_days: int = 7, min_misses: int = 3) -> list[DisappearedListing]:
        """The disappearances get_disappeared would report once this run's
        miss counts land, without writing them: absent listings evaluated
        one miss ahead, present ones at zero. Lets the pipeline compute the
        notification before the send it must not corrupt state ahead of."""
        candidates = self._tracked_within_window(profile_id, max_age_days)
        result = []
        for row in candidates:
            if row["id"] in current_ids:
                continue
            pending_miss_count = row["miss_count"] + 1
            if pending_miss_count >= min_misses:
                result.append(self._to_disappeared_listing(row))
        return result

    def _tracked_within_window(self, profile_id: str, max_age_days: int) -> list[sqlite3.Row]:
        """Every listing_tracking row for the profile whose first_seen_at is
        recent enough to ever qualify as disappeared, joined with the
        listing, property, and latest-price facts a report needs.

        Reported only while recently first seen: an old listing that finally
        drops off is stale, not news.
        """
        cutoff = (self._now() - timedelta(days=max_age_days)).isoformat()
        # Latest price observation per listing: highest id wins ties on
        # observed_at, since id is monotonic insertion order and observed_at
        # is not guaranteed distinct.
        stmt = """
            SELECT listings.id AS id, listings.source AS source, listings.url AS url,
                   listing_tracking.first_seen_at AS first_seen_at,
                   listing_tracking.miss_count AS miss_count,
                   properties.title AS title, properties.location AS location,
                   latest_price.price AS price
            FROM listing_tracking
            JOIN listings ON listings.id = listing_tracking.listing_id
            JOIN properties ON properties.id = listings.property_id
            LEFT JOIN price_observations AS latest_price
                ON latest_price.id = (
                    SELECT id FROM price_observations
                    WHERE listing_id = listings.id
                    ORDER BY observed_at DESC, id DESC
                    LIMIT 1
                )
            WHERE listing_tracking.profile_id = ? AND listing_tracking.first_seen_at >= ?
        """
        return self._conn.execute(stmt, (profile_id, cutoff)).fetchall()

    def prune(self, profile_id: str, max_age_days: int = 90) -> int:
        """Forgets the profile's stale tracking rows. Listing facts, price
        history, and properties survive as global history."""
        cutoff = (self._now() - timedelta(days=max_age_days)).isoformat()
        stmt = """
            DELETE FROM listing_tracking
            WHERE profile_id = ? AND last_seen_at < ? AND favourited_at IS NULL
        """
        cursor = self._conn.execute(stmt, (profile_id, cutoff))
        self._conn.commit()
        return cursor.rowcount
