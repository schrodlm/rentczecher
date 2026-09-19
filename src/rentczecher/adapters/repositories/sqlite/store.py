import sqlite3
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.repositories.sqlite.listings import SqliteListingRepository
from rentczecher.adapters.repositories.sqlite.profiles import SqliteProfileRepository
from rentczecher.adapters.repositories.sqlite.properties import SqlitePropertyRepository
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.listing import DisappearedListing
from rentczecher.services.assemble import assemble_property
from rentczecher.services.dedup import DedupOutcome, match_score_to_json


class SqliteRunStore:
    """Everything one profile run reads and persists, behind one object.

    The pipeline reads seen state and prices before deciding what is new,
    then persists the whole outcome only after the notification succeeded.
    """

    def __init__(self, conn: sqlite3.Connection, *, now: Callable[[], datetime] = utc_now):
        self._conn = conn
        self._listings = SqliteListingRepository(conn, now=now)
        self._properties = SqlitePropertyRepository(conn, now=now)
        self._profiles = SqliteProfileRepository(conn, now=now)
        self._now = now

    def seen_ids(self, profile_id: str) -> set[str]:
        return self._listings.seen_ids(profile_id)

    def latest_prices(self, profile_id: str) -> dict[str, int]:
        return self._listings.latest_prices(profile_id)

    def pending_disappeared(self, profile_id: str, current_ids: set[str]) -> list[DisappearedListing]:
        return self._listings.pending_disappeared(profile_id, current_ids)

    def prune(self, profile_id: str) -> None:
        """Forgets the profile's stale tracking rows, its own unit of work."""
        try:
            self._listings.prune(profile_id)
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def persist_outcome(self, profile_id: str, profile_name: str, outcome: DedupOutcome,
                        located_by_id: dict[str, Listing], current_ids: set[str]) -> None:
        """Writes the run's facts in one transaction: the profile row, one
        property per real-world unit, a listing row per portal posting
        (absorbed ones included, under their keeper's property), the dedup
        audit trail, and the miss-count increments for listings absent this
        run. Nothing commits if any step raises."""
        try:
            self._profiles.ensure(profile_id, profile_name)
            now = self._now().isoformat()
            keeper_ids = outcome.final_keeper_ids()

            members_by_keeper: dict[str, list[Listing]] = {}
            for listing in outcome.survivors:
                members_by_keeper[listing.id] = [listing]
            for absorbed_id, keeper_id in keeper_ids.items():
                members_by_keeper[keeper_id].append(located_by_id[absorbed_id])

            property_by_keeper = {
                keeper_id: self._property_for(members, now)
                for keeper_id, members in members_by_keeper.items()
            }

            for keeper_id, members in members_by_keeper.items():
                for listing in members:
                    self._listings.upsert(
                        profile_id, property_by_keeper[keeper_id], listing)

            for merge in outcome.merges:
                self._properties.record_dedup(
                    property_by_keeper[keeper_ids[merge.absorbed_id]],
                    merge.absorbed_id, match_score_to_json(merge.score))
            # An uncertain pair never merges: the record points one side's
            # listing at the other side's property, so the doubt is auditable.
            for pair in outcome.uncertain:
                property_id = self._listings.property_id_of(pair.listing_id_a)
                if property_id is not None:
                    self._properties.record_dedup(
                        property_id, pair.listing_id_b, match_score_to_json(pair.score))

            self._listings.increment_miss_counts(profile_id, current_ids)
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def _property_for(self, members: list[Listing], now: str) -> str:
        """The property a merge group lands on: the keeper's existing one
        when it has one, else any member's existing one, else a new one
        seeded from the keeper. A member's other property folds into the
        winner as a tombstone. Members arrive keeper first."""
        existing: list[str] = []
        for listing in members:
            property_id = self._listings.property_id_of(listing.id)
            if property_id is not None and property_id not in existing:
                existing.append(property_id)
        if not existing:
            identity = assemble_property(members[0], property_id=str(uuid4()), created_at=now)
            self._properties.create(identity)
            return identity.id
        winner = existing[0]
        for loser in existing[1:]:
            self._properties.fold_into(loser, winner)
        return winner
