import sqlite3
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.domain.disposition import Disposition, parse_disposition
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria, Portal, Preferences, Profile


class SqliteProfileRepository:
    """Profiles with their criteria, portals and preferences, each part in
    its own table."""

    def __init__(self, conn: sqlite3.Connection, *, now: Callable[[], datetime] = utc_now):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._now = now

    def add(self, name: str, portals: tuple[Portal, ...], criteria: Criteria, preferences: Preferences) -> Profile:
        """Stores a new, unpaused profile and returns it as it reads back:
        with its generated id, and its portals and accepted dispositions,
        which have no order, sorted."""
        accepted = tuple(sorted(criteria.dispositions, key=lambda disposition: disposition.code))
        profile = Profile(
            id=str(uuid4()),
            name=name,
            paused_at=None,
            portals=tuple(sorted(portals)),
            criteria=replace(criteria, dispositions=accepted),
            preferences=preferences,
        )
        stmt = """
            INSERT INTO profiles (id, name, paused_at, created_at)
            VALUES (?, ?, NULL, ?)
        """
        self._conn.execute(stmt, (profile.id, profile.name, self._now().isoformat()))
        self._insert_criteria(profile.id, profile.criteria)
        self._insert_portals(profile.id, profile.portals)
        self._insert_preferences(profile.id, profile.preferences)
        return profile

    def update(self, profile_id: str, name: str, paused: bool, portals: tuple[Portal, ...],
               preferences: Preferences) -> Profile | None:
        """Everything but the criteria, which stay as created. None for an
        unknown id."""
        current = self.get(profile_id)
        if current is None:
            return None
        if not paused:
            paused_at = None
        elif current.paused_at is None:
            paused_at = self._now().isoformat()
        else:
            paused_at = current.paused_at
        profile = Profile(
            id=profile_id,
            name=name,
            paused_at=paused_at,
            portals=tuple(sorted(portals)),
            criteria=current.criteria,
            preferences=preferences,
        )
        stmt = "UPDATE profiles SET name = ?, paused_at = ? WHERE id = ?"
        # The profile may have been deleted on another connection since the read.
        if self._conn.execute(stmt, (profile.name, profile.paused_at, profile.id)).rowcount == 0:
            return None
        self._delete_portals_and_preferences(profile.id)
        self._insert_portals(profile.id, profile.portals)
        self._insert_preferences(profile.id, profile.preferences)
        return profile

    def delete(self, profile_id: str) -> bool:
        """Whether the profile existed. Its listings stay."""
        stmt = "DELETE FROM profiles WHERE id = ?"
        return self._conn.execute(stmt, (profile_id,)).rowcount == 1

    def get(self, profile_id: str) -> Profile | None:
        stmt = """
            SELECT p.id, p.name, p.paused_at,
                   c.offer_type, c.estate_type, c.place_kind, c.place_code, c.min_price, c.max_price,
                   c.min_size_m2, c.max_size_m2, c.min_land_m2,
                   r.price_per_m2_weight, r.disposition_weight, r.size_weight, r.preferred_size_m2,
                   r.place_weight, r.land_weight, r.preferred_land_m2, r.price_weight, r.preferred_price
            FROM profiles p
            JOIN profile_criteria c ON c.profile_id = p.id
            JOIN profile_preferences r ON r.profile_id = p.id
            WHERE p.id = ?
        """
        row = self._conn.execute(stmt, (profile_id,)).fetchone()
        return self._read_profile(row) if row is not None else None

    def list_profiles(self) -> list[Profile]:
        """Every profile, oldest first."""
        stmt = """
            SELECT p.id, p.name, p.paused_at,
                   c.offer_type, c.estate_type, c.place_kind, c.place_code, c.min_price, c.max_price,
                   c.min_size_m2, c.max_size_m2, c.min_land_m2,
                   r.price_per_m2_weight, r.disposition_weight, r.size_weight, r.preferred_size_m2,
                   r.place_weight, r.land_weight, r.preferred_land_m2, r.price_weight, r.preferred_price
            FROM profiles p
            JOIN profile_criteria c ON c.profile_id = p.id
            JOIN profile_preferences r ON r.profile_id = p.id
            ORDER BY p.created_at, p.id
        """
        return [self._read_profile(row) for row in self._conn.execute(stmt).fetchall()]

    def _read_profile(self, row: sqlite3.Row) -> Profile:
        """The profile a joined row holds, with the lists kept in their own tables."""
        profile_id = row["id"]
        return self._to_profile(
            row,
            portals=self._portals(profile_id),
            accepted_dispositions=self._accepted_dispositions(profile_id),
            preferred_dispositions=self._preferred_dispositions(profile_id),
            preferred_places=self._preferred_places(profile_id),
        )

    def _delete_portals_and_preferences(self, profile_id: str) -> None:
        stmt = "DELETE FROM profile_portals WHERE profile_id = ?"
        self._conn.execute(stmt, (profile_id,))
        stmt = "DELETE FROM profile_preferences WHERE profile_id = ?"
        self._conn.execute(stmt, (profile_id,))
        stmt = "DELETE FROM preferred_dispositions WHERE profile_id = ?"
        self._conn.execute(stmt, (profile_id,))
        stmt = "DELETE FROM preferred_places WHERE profile_id = ?"
        self._conn.execute(stmt, (profile_id,))

    def _insert_criteria(self, profile_id: str, criteria: Criteria) -> None:
        stmt = """
            INSERT INTO profile_criteria
                (profile_id, offer_type, estate_type, place_kind, place_code, min_price, max_price,
                 min_size_m2, max_size_m2, min_land_m2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.execute(stmt, (
            profile_id,
            criteria.offer_type,
            criteria.estate_type,
            criteria.place.kind,
            criteria.place.code,
            criteria.min_price,
            criteria.max_price,
            criteria.min_size_m2,
            criteria.max_size_m2,
            criteria.min_land_m2,
        ))
        stmt = "INSERT INTO accepted_dispositions (profile_id, disposition) VALUES (?, ?)"
        for disposition in criteria.dispositions:
            self._conn.execute(stmt, (profile_id, disposition.code))

    def _insert_portals(self, profile_id: str, portals: tuple[Portal, ...]) -> None:
        stmt = "INSERT INTO profile_portals (profile_id, portal) VALUES (?, ?)"
        for portal in portals:
            self._conn.execute(stmt, (profile_id, portal))

    def _insert_preferences(self, profile_id: str, preferences: Preferences) -> None:
        stmt = """
            INSERT INTO profile_preferences
                (profile_id, price_per_m2_weight, disposition_weight, size_weight, preferred_size_m2,
                 place_weight, land_weight, preferred_land_m2, price_weight, preferred_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.execute(stmt, (
            profile_id,
            preferences.price_per_m2_weight,
            preferences.disposition_weight,
            preferences.size_weight,
            preferences.preferred_size_m2,
            preferences.place_weight,
            preferences.land_weight,
            preferences.preferred_land_m2,
            preferences.price_weight,
            preferences.preferred_price,
        ))
        stmt = "INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES (?, ?, ?)"
        for rank, disposition in enumerate(preferences.preferred_dispositions, start=1):
            self._conn.execute(stmt, (profile_id, disposition.code, rank))
        stmt = "INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) VALUES (?, ?, ?, ?)"
        for rank, place in enumerate(preferences.preferred_places, start=1):
            self._conn.execute(stmt, (profile_id, place.kind, place.code, rank))

    def _to_profile(self, row: sqlite3.Row, portals: tuple[Portal, ...],
                    accepted_dispositions: tuple[Disposition, ...],
                    preferred_dispositions: tuple[Disposition, ...],
                    preferred_places: tuple[PlaceRef, ...]) -> Profile:
        return Profile(
            id=row["id"],
            name=row["name"],
            paused_at=row["paused_at"],
            portals=portals,
            criteria=self._to_criteria(row, accepted_dispositions),
            preferences=self._to_preferences(row, preferred_dispositions, preferred_places),
        )

    def _to_criteria(self, row: sqlite3.Row, accepted_dispositions: tuple[Disposition, ...]) -> Criteria:
        return Criteria(
            offer_type=row["offer_type"],
            estate_type=row["estate_type"],
            place=PlaceRef(kind=row["place_kind"], code=row["place_code"]),
            min_price=row["min_price"],
            max_price=row["max_price"],
            min_size_m2=row["min_size_m2"],
            max_size_m2=row["max_size_m2"],
            min_land_m2=row["min_land_m2"],
            dispositions=accepted_dispositions,
        )

    def _to_preferences(self, row: sqlite3.Row, preferred_dispositions: tuple[Disposition, ...],
                        preferred_places: tuple[PlaceRef, ...]) -> Preferences:
        return Preferences(
            price_per_m2_weight=row["price_per_m2_weight"],
            disposition_weight=row["disposition_weight"],
            preferred_dispositions=preferred_dispositions,
            size_weight=row["size_weight"],
            preferred_size_m2=row["preferred_size_m2"],
            place_weight=row["place_weight"],
            preferred_places=preferred_places,
            land_weight=row["land_weight"],
            preferred_land_m2=row["preferred_land_m2"],
            price_weight=row["price_weight"],
            preferred_price=row["preferred_price"],
        )

    def _portals(self, profile_id: str) -> tuple[Portal, ...]:
        stmt = "SELECT portal FROM profile_portals WHERE profile_id = ? ORDER BY portal"
        return tuple(row["portal"] for row in self._conn.execute(stmt, (profile_id,)))

    def _accepted_dispositions(self, profile_id: str) -> tuple[Disposition, ...]:
        stmt = "SELECT disposition FROM accepted_dispositions WHERE profile_id = ? ORDER BY disposition"
        return tuple(_stored_disposition(row["disposition"]) for row in self._conn.execute(stmt, (profile_id,)))

    def _preferred_dispositions(self, profile_id: str) -> tuple[Disposition, ...]:
        stmt = "SELECT disposition FROM preferred_dispositions WHERE profile_id = ? ORDER BY rank"
        return tuple(_stored_disposition(row["disposition"]) for row in self._conn.execute(stmt, (profile_id,)))

    def _preferred_places(self, profile_id: str) -> tuple[PlaceRef, ...]:
        stmt = "SELECT place_kind, place_code FROM preferred_places WHERE profile_id = ? ORDER BY rank"
        return tuple(PlaceRef(kind=row["place_kind"], code=row["place_code"])
                     for row in self._conn.execute(stmt, (profile_id,)))


def _stored_disposition(code: str) -> Disposition:
    disposition = parse_disposition(code)
    # The dispositions table holds only codes the parser reads back.
    assert disposition is not None
    return disposition
