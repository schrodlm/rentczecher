import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta

from rentczecher.adapters.repositories.repositories import ListingRepository
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.listing import DisappearedListing, InboxCard, SiblingSource
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
        """Reconciles a scraped observation into storage without committing.
        The caller owns the transaction boundary."""
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

    def mark_viewed(self, profile_id: str, listing_id: str) -> None:
        """Records the listing as viewed by the profile, without committing.
        The caller owns the transaction boundary.

        Viewed is set once: an already-viewed listing keeps its first
        viewed_at, since viewing it again is not a new event.
        """
        stmt = """
            UPDATE listing_tracking SET viewed_at = ?
            WHERE profile_id = ? AND listing_id = ? AND viewed_at IS NULL
        """
        self._conn.execute(stmt, (self._now().isoformat(), profile_id, listing_id))

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

    def inbox_listings(self, profile_id: str, only_new: bool = False) -> list[InboxCard]:
        """The profile's tracked listings as the GUI's inbox renders them:
        listing and property facts, this profile's tracking state, the
        latest price, a price-drop baseline, and sibling postings on other
        portals. only_new restricts to listings never viewed by the profile.
        """
        # Latest and previous price observation per listing: highest id wins
        # ties on observed_at, since id is monotonic insertion order and
        # observed_at is not guaranteed distinct.
        stmt = """
            SELECT listings.id AS id, listings.source AS source, listings.url AS url,
                   listings.property_id AS property_id,
                   properties.title AS title, properties.location AS location,
                   properties.size_m2 AS size_m2, properties.disposition AS disposition,
                   listing_tracking.first_seen_at AS first_seen_at,
                   listing_tracking.viewed_at AS viewed_at,
                   listing_tracking.favourited_at AS favourited_at,
                   latest_price.price AS price,
                   previous_price.price AS previous_price
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
            LEFT JOIN price_observations AS previous_price
                ON previous_price.id = (
                    SELECT id FROM price_observations
                    WHERE listing_id = listings.id
                    ORDER BY observed_at DESC, id DESC
                    LIMIT 1 OFFSET 1
                )
            WHERE listing_tracking.profile_id = ?
        """
        params: tuple = (profile_id,)
        if only_new:
            stmt += " AND listing_tracking.viewed_at IS NULL"
        rows = self._conn.execute(stmt, params).fetchall()
        listings_by_property = self._listings_by_property({row["property_id"] for row in rows})
        return [self._to_inbox_card(row, listings_by_property) for row in rows]

    def _listings_by_property(
        self, property_ids: set[str],
    ) -> dict[str, list[tuple[str, SiblingSource]]]:
        """Every listing posted under each given property, keyed by
        property_id and paired with its own id - the take-na badge's raw
        data before a card excludes its own listing from its own sibling
        list."""
        if not property_ids:
            return {}
        placeholders = ", ".join("?" for _ in property_ids)
        stmt = f"""
            SELECT id, property_id, source, url FROM listings
            WHERE property_id IN ({placeholders})
        """
        result: dict[str, list[tuple[str, SiblingSource]]] = {pid: [] for pid in property_ids}
        for row in self._conn.execute(stmt, tuple(property_ids)):
            result[row["property_id"]].append(
                (row["id"], SiblingSource(source=row["source"], url=row["url"])))
        return result

    def _to_inbox_card(
        self, row: sqlite3.Row, listings_by_property: dict[str, list[tuple[str, SiblingSource]]],
    ) -> InboxCard:
        price_drop_from = None
        if row["price"] is not None and row["previous_price"] is not None \
                and row["previous_price"] > row["price"]:
            price_drop_from = row["previous_price"]
        siblings = tuple(
            sibling for listing_id, sibling in listings_by_property.get(row["property_id"], [])
            if listing_id != row["id"]
        )
        return InboxCard(
            id=row["id"],
            source=row["source"],
            url=row["url"],
            title=row["title"],
            location=row["location"],
            size_m2=row["size_m2"],
            disposition=row["disposition"],
            first_seen_at=row["first_seen_at"],
            viewed_at=row["viewed_at"],
            favourited_at=row["favourited_at"],
            price=row["price"],
            price_drop_from=price_drop_from,
            sibling_sources=siblings,
        )

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
        return cursor.rowcount
