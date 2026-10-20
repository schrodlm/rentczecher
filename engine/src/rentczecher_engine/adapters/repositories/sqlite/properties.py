import json
import sqlite3
from collections.abc import Callable
from datetime import datetime

from rentczecher_engine.adapters.repositories.repositories import PropertyRepository
from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.domain.disposition import parse_disposition
from rentczecher_engine.domain.geo import geocell
from rentczecher_engine.domain.property import PropertyIdentity, PropertyLocation


class SqlitePropertyRepository(PropertyRepository):
    def __init__(self, conn: sqlite3.Connection, *, now: Callable[[], datetime] = utc_now):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row  # column-name indexing on rows
        self._now = now

    def _to_identity(self, row: sqlite3.Row) -> PropertyIdentity:
        return PropertyIdentity(
            id=row["id"],
            created_at=row["created_at"],
            merged_into=row["merged_into"],
            title=row["title"],
            location_raw_text=row["location_raw_text"],
            size_m2=row["size_m2"],
            disposition_raw_text=row["disposition_raw_text"],
            disposition=parse_disposition(row["disposition_code"]),
            lat=row["lat"],
            lon=row["lon"],
            land_m2=row["land_m2"],
        )

    def _to_location(self, row: sqlite3.Row) -> PropertyLocation:
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

    def get(self, property_id: str) -> PropertyIdentity | None:
        stmt = """
            SELECT id, created_at, merged_into, title, location_raw_text,
                   size_m2, disposition_raw_text, disposition_code, lat, lon, land_m2
            FROM properties WHERE id = ?
        """
        row = self._conn.execute(stmt, (property_id,)).fetchone()
        return self._to_identity(row) if row else None

    def create(self, identity: PropertyIdentity) -> None:
        cell_lat, cell_lon = (
            geocell(identity.lat, identity.lon)
            if identity.lat is not None and identity.lon is not None
            else (None, None)
        )
        stmt = """
            INSERT INTO properties (
                id, created_at, merged_into, title, location_raw_text,
                size_m2, disposition_raw_text, disposition_code, lat, lon, land_m2, cell_lat, cell_lon
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.execute(stmt, (
            identity.id, identity.created_at, identity.merged_into,
            identity.title, identity.location_raw_text, identity.size_m2,
            identity.disposition_raw_text,
            identity.disposition.code if identity.disposition is not None else None,
            identity.lat, identity.lon, identity.land_m2,
            cell_lat, cell_lon,
        ))

    def location(self, property_id: str) -> PropertyLocation | None:
        stmt = """
            SELECT kraj_code, okres_code, obec_code, obvod_code, mestska_cast_code,
                   cast_obce_code, ulice_code, cislo_popisne, cislo_orientacni
            FROM property_locations WHERE property_id = ?
        """
        row = self._conn.execute(stmt, (property_id,)).fetchone()
        return self._to_location(row) if row else None

    def save_location(self, property_id: str, location: PropertyLocation) -> None:
        stmt = """
            INSERT INTO property_locations (
                property_id, kraj_code, okres_code, obec_code, obvod_code, mestska_cast_code,
                cast_obce_code, ulice_code, cislo_popisne, cislo_orientacni
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (property_id) DO UPDATE SET
                kraj_code = excluded.kraj_code,
                okres_code = excluded.okres_code,
                obec_code = excluded.obec_code,
                obvod_code = excluded.obvod_code,
                mestska_cast_code = excluded.mestska_cast_code,
                cast_obce_code = excluded.cast_obce_code,
                ulice_code = excluded.ulice_code,
                cislo_popisne = excluded.cislo_popisne,
                cislo_orientacni = excluded.cislo_orientacni
        """
        self._conn.execute(stmt, (
            property_id, location.kraj_code, location.okres_code, location.obec_code,
            location.obvod_code, location.mestska_cast_code, location.cast_obce_code,
            location.ulice_code, location.cislo_popisne, location.cislo_orientacni,
        ))

    def fold_into(self, loser_id: str, winner_id: str) -> None:
        """Marks the loser as merged into the winner. A folded property is a
        tombstone: it stays while a profile tracks it or another property is
        folded into it, but is never a merge target. Each profile's tracking of
        the loser is copied onto the winner, where the flat stays viewed and
        starred since the first of the two was. The loser keeps its own, since
        a listing the merge did not move stays on it and still shows there.
        A request for the loser's whole gallery carries over to the winner."""
        stmt = "UPDATE properties SET merged_into = ? WHERE id = ?"
        self._conn.execute(stmt, (winner_id, loser_id))
        stmt = """
            INSERT INTO property_tracking (profile_id, property_id, viewed_at, favourited_at)
            SELECT profile_id, ?, viewed_at, favourited_at FROM property_tracking WHERE property_id = ?
            ON CONFLICT (profile_id, property_id) DO UPDATE SET
                viewed_at = CASE
                    WHEN property_tracking.viewed_at IS NULL THEN excluded.viewed_at
                    WHEN excluded.viewed_at IS NULL THEN property_tracking.viewed_at
                    ELSE min(property_tracking.viewed_at, excluded.viewed_at)
                END,
                favourited_at = CASE
                    WHEN property_tracking.favourited_at IS NULL THEN excluded.favourited_at
                    WHEN excluded.favourited_at IS NULL THEN property_tracking.favourited_at
                    ELSE min(property_tracking.favourited_at, excluded.favourited_at)
                END
        """
        self._conn.execute(stmt, (winner_id, loser_id))
        stmt = """
            INSERT INTO gallery_requests (property_id, requested_at)
            SELECT ?, requested_at FROM gallery_requests WHERE property_id = ?
            ON CONFLICT (property_id) DO NOTHING
        """
        self._conn.execute(stmt, (winner_id, loser_id))

    def forget_untracked(self) -> None:
        """Deletes every property no profile has starred or tracks through a
        listing any more, and with it everything read about it. A property
        another one is folded into goes only after that one, so each pass
        removes the outermost folds."""
        stmt = """
            DELETE FROM properties
            WHERE id NOT IN (SELECT property_id FROM property_tracking WHERE favourited_at IS NOT NULL)
              AND id NOT IN (
                  SELECT listings.property_id FROM listing_tracking
                  JOIN listings ON listings.id = listing_tracking.listing_id
              )
              AND id NOT IN (SELECT merged_into FROM properties WHERE merged_into IS NOT NULL)
        """
        deleted = self._conn.execute(stmt).rowcount
        while deleted > 0:
            deleted = self._conn.execute(stmt).rowcount

    def attach_listing(self, property_id: str, listing_id: str) -> None:
        stmt = "UPDATE listings SET property_id = ? WHERE id = ?"
        self._conn.execute(stmt, (property_id, listing_id))

    def record_dedup(self, property_id: str, listing_id: str, match_reason: str,
                     differences: dict | None = None) -> None:
        stmt = """
            INSERT INTO dedup_records (
                property_id, listing_id, match_reason, differences, decided_at
            ) VALUES (?, ?, ?, ?, ?)
        """
        self._conn.execute(stmt, (
            property_id, listing_id, match_reason,
            json.dumps(differences) if differences is not None else None,
            self._now().isoformat(),
        ))

    def find_candidates(self, cell_lat: int, cell_lon: int) -> list[PropertyIdentity]:
        stmt = """
            SELECT id, created_at, merged_into, title, location_raw_text,
                   size_m2, disposition_raw_text, disposition_code, lat, lon, land_m2
            FROM properties
            WHERE merged_into IS NULL
              AND cell_lat BETWEEN ? - 1 AND ? + 1
              AND cell_lon BETWEEN ? - 1 AND ? + 1
        """
        rows = self._conn.execute(stmt, (cell_lat, cell_lat, cell_lon, cell_lon)).fetchall()
        return [self._to_identity(row) for row in rows]
