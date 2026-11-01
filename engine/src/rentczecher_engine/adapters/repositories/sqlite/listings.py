import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta

from rentczecher_engine.adapters.repositories.repositories import ListingRepository
from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.domain.disposition import parse_disposition
from rentczecher_engine.domain.geo import GeoPoint
from rentczecher_engine.domain.price import PostingPrices, PriceObservation, price_changes
from rentczecher_engine.domain.property import PropertyLocation, SiblingSource, TrackedProperty


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
        self._track_property(profile_id, property_id)
        self.record_price_observation(PriceObservation(
            listing_id=listing.id, price=listing.price,
            charges=listing.charges, observed_at=now))

    def _track_property(self, profile_id: str, property_id: str) -> None:
        """Tracks the property for the profile, indexed next in the order
        the profile found its flats, unless it already does."""
        stmt = "SELECT 1 FROM property_tracking WHERE profile_id = ? AND property_id = ?"
        if self._conn.execute(stmt, (profile_id, property_id)).fetchone() is not None:
            return
        stmt = """
            INSERT INTO property_tracking (profile_id, property_id, profile_index)
            SELECT ?, ?, coalesce(max(profile_index), 0) + 1 FROM property_tracking WHERE profile_id = ?
        """
        self._conn.execute(stmt, (profile_id, property_id, profile_id))

    def mark_viewed(self, profile_id: str, property_id: str) -> None:
        """Records the property as viewed by the profile, without
        committing. The caller owns the transaction boundary.

        Viewed is set once: an already-viewed property keeps its first
        viewed_at, since viewing it again is not a new event.
        """
        stmt = """
            UPDATE property_tracking SET viewed_at = ?
            WHERE profile_id = ? AND property_id = ? AND viewed_at IS NULL
        """
        self._conn.execute(stmt, (self._now().isoformat(), profile_id, property_id))

    def mark_favourite(self, profile_id: str, property_id: str) -> None:
        """Records the property as the profile's favourite and views it,
        without committing. A favourite keeps its first favourited_at, and
        a viewed property its first viewed_at.
        """
        now = self._now().isoformat()
        stmt = """
            UPDATE property_tracking
            SET favourited_at = coalesce(favourited_at, ?), viewed_at = coalesce(viewed_at, ?)
            WHERE profile_id = ? AND property_id = ?
        """
        self._conn.execute(stmt, (now, now, profile_id, property_id))

    def clear_favourite(self, profile_id: str, property_id: str) -> None:
        """Stops keeping the property as a favourite, without committing."""
        stmt = """
            UPDATE property_tracking SET favourited_at = NULL
            WHERE profile_id = ? AND property_id = ?
        """
        self._conn.execute(stmt, (profile_id, property_id))

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

    def price_histories(self, profile_id: str, property_id: str) -> list[PostingPrices] | None:
        stmt = """
            SELECT listings.id AS id, listings.source AS source, listings.url AS url
            FROM listings
            JOIN listing_tracking ON listing_tracking.listing_id = listings.id
            WHERE listings.property_id = ? AND listing_tracking.profile_id = ?
            ORDER BY listings.source, listings.id
        """
        postings = [self._to_posting_prices(row) for row in self._conn.execute(stmt, (property_id, profile_id))]
        if not postings:
            return None
        return postings

    def _to_posting_prices(self, row: sqlite3.Row) -> PostingPrices:
        return PostingPrices(
            listing_id=row["id"],
            source=row["source"],
            url=row["url"],
            changes=tuple(price_changes(self.price_history(row["id"]))),
        )

    def latest_prices(self, profile_id: str) -> dict[str, int]:
        """The price per listing the profile tracks as the profile's own scans
        last saw it, so another profile's later scan never hides a change.

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
                        AND observed_at <= listing_tracking.last_seen_at
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

    def pending_disappeared(self, profile_id: str, current_ids: set[str],
                            max_age_days: int = 7, min_misses: int = 3) -> set[str]:
        """Lets the pipeline count this run's disappearances before it
        persists the run."""
        candidates = self._tracked_within_window(profile_id, max_age_days)
        return {
            row["listing_id"]
            for row in candidates
            if row["listing_id"] not in current_ids and row["miss_count"] + 1 >= min_misses
        }

    def tracked_properties(self, profile_id: str, only_new: bool = False) -> list[TrackedProperty]:
        """Every property the profile tracks, or with only_new those it never
        viewed, each made of the listings of it the profile tracks."""
        # Latest and previous price observation per listing: highest id wins
        # ties on observed_at, since id is monotonic insertion order and
        # observed_at is not guaranteed distinct.
        stmt = """
            SELECT listings.id AS id, listings.source AS source, listings.url AS url,
                   listings.property_id AS property_id,
                   properties.title AS title, properties.location_raw_text AS location_raw_text,
                   properties.size_m2 AS size_m2, properties.land_m2 AS land_m2,
                   properties.disposition_raw_text AS disposition_raw_text,
                   properties.disposition_code AS disposition_code,
                   properties.lat AS lat, properties.lon AS lon,
                   property_locations.kraj_code AS kraj_code,
                   property_locations.okres_code AS okres_code,
                   property_locations.obec_code AS obec_code,
                   property_locations.obvod_code AS obvod_code,
                   property_locations.mestska_cast_code AS mestska_cast_code,
                   property_locations.cast_obce_code AS cast_obce_code,
                   property_locations.ulice_code AS ulice_code,
                   property_locations.cislo_popisne AS cislo_popisne,
                   property_locations.cislo_orientacni AS cislo_orientacni,
                   listing_tracking.first_seen_at AS first_seen_at,
                   property_tracking.profile_index AS profile_index,
                   property_tracking.viewed_at AS viewed_at,
                   property_tracking.favourited_at AS favourited_at,
                   latest_price.price AS price,
                   previous_price.price AS previous_price
            FROM property_tracking
            JOIN listings ON listings.property_id = property_tracking.property_id
            JOIN listing_tracking ON listing_tracking.listing_id = listings.id
                AND listing_tracking.profile_id = property_tracking.profile_id
            JOIN properties ON properties.id = listings.property_id
            LEFT JOIN property_locations ON property_locations.property_id = properties.id
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
                    WHERE listing_id = listings.id AND price != latest_price.price
                    ORDER BY observed_at DESC, id DESC
                    LIMIT 1
                )
            WHERE property_tracking.profile_id = ?
        """
        if only_new:
            stmt += " AND property_tracking.viewed_at IS NULL"
        listings_by_property: dict[str, list[sqlite3.Row]] = {}
        for row in self._conn.execute(stmt, (profile_id,)):
            listings_by_property.setdefault(row["property_id"], []).append(row)
        return [self._to_tracked_property(listings) for listings in listings_by_property.values()]

    def _to_tracked_property(self, listings: list[sqlite3.Row]) -> TrackedProperty:
        """The property as the profile tracks it, shown by its cheapest
        listing, the first found among equally cheap ones. It was first seen
        when the first of its listings was."""
        row = min(listings, key=lambda listing: (
            listing["price"] is None, listing["price"] or 0, listing["first_seen_at"], listing["id"]))
        price_drop_from = None
        if row["price"] is not None and row["previous_price"] is not None \
                and row["previous_price"] > row["price"]:
            price_drop_from = row["previous_price"]
        siblings = tuple(
            SiblingSource(source=listing["source"], url=listing["url"])
            for listing in sorted(listings, key=lambda listing: listing["source"])
            if listing["id"] != row["id"]
        )
        return TrackedProperty(
            id=row["property_id"],
            index=row["profile_index"],
            listing_id=row["id"],
            source=row["source"],
            url=row["url"],
            title=row["title"],
            location_raw_text=row["location_raw_text"],
            property_location=self._to_property_location(row) if row["kraj_code"] is not None else None,
            point=GeoPoint(lat=row["lat"], lon=row["lon"]) if row["lat"] is not None and row["lon"] is not None else None,
            size_m2=row["size_m2"],
            land_m2=row["land_m2"],
            disposition_raw_text=row["disposition_raw_text"],
            disposition=parse_disposition(row["disposition_code"]),
            first_seen_at=min(listing["first_seen_at"] for listing in listings),
            viewed_at=row["viewed_at"],
            favourited_at=row["favourited_at"],
            price=row["price"],
            price_drop_from=price_drop_from,
            sibling_sources=siblings,
        )

    def _to_property_location(self, row: sqlite3.Row) -> PropertyLocation:
        return PropertyLocation(
            kraj_code=row["kraj_code"],
            okres_code=row["okres_code"],
            obec_code=row["obec_code"],
            obvod_code=row["obvod_code"],
            mestska_cast_code=row["mestska_cast_code"],
            cast_obce_code=row["cast_obce_code"],
            ulice_code=row["ulice_code"],
            cislo_popisne=row["cislo_popisne"],
            cislo_orientacni=row["cislo_orientacni"],
        )

    def _tracked_within_window(self, profile_id: str, max_age_days: int) -> list[sqlite3.Row]:
        """Every listing_tracking row for the profile first seen recently
        enough to count as disappeared, with its miss count.

        Reported only while recently first seen: an old listing that finally
        drops off is stale, not news.
        """
        cutoff = (self._now() - timedelta(days=max_age_days)).isoformat()
        stmt = """
            SELECT listing_id, miss_count
            FROM listing_tracking
            WHERE profile_id = ? AND first_seen_at >= ?
        """
        return self._conn.execute(stmt, (profile_id, cutoff)).fetchall()

    def prune(self, profile_id: str, max_age_days: int = 90) -> int:
        """Forgets the profile's stale tracking of listings, then of the
        properties none of its listings is tracked under any more. A favourite
        property and its listings are kept. Returns how many listings were
        forgotten."""
        cutoff = (self._now() - timedelta(days=max_age_days)).isoformat()
        stmt = """
            DELETE FROM listing_tracking
            WHERE profile_id = ? AND last_seen_at < ?
              AND listing_id NOT IN (
                  SELECT listings.id FROM listings
                  JOIN property_tracking ON property_tracking.property_id = listings.property_id
                  WHERE property_tracking.profile_id = ? AND property_tracking.favourited_at IS NOT NULL
              )
        """
        cursor = self._conn.execute(stmt, (profile_id, cutoff, profile_id))
        stmt = """
            DELETE FROM property_tracking
            WHERE profile_id = ? AND favourited_at IS NULL
              AND property_id NOT IN (
                  SELECT listings.property_id FROM listing_tracking
                  JOIN listings ON listings.id = listing_tracking.listing_id
                  WHERE listing_tracking.profile_id = ?
              )
        """
        self._conn.execute(stmt, (profile_id, profile_id))
        return cursor.rowcount
