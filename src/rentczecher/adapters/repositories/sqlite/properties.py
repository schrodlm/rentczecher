import json
import sqlite3
from collections.abc import Callable
from datetime import datetime

from rentczecher.adapters.repositories.repositories import PropertyRepository
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.domain.geo import geocell
from rentczecher.domain.property import PropertyIdentity


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
            location=row["location"],
            size_m2=row["size_m2"],
            disposition=row["disposition"],
            lat=row["lat"],
            lon=row["lon"],
            land_m2=row["land_m2"],
        )

    def get(self, property_id: str) -> PropertyIdentity | None:
        stmt = """
            SELECT id, created_at, merged_into, title, location,
                   size_m2, disposition, lat, lon, land_m2
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
                id, created_at, merged_into, title, location,
                size_m2, disposition, lat, lon, land_m2, cell_lat, cell_lon
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.execute(stmt, (
            identity.id, identity.created_at, identity.merged_into,
            identity.title, identity.location, identity.size_m2,
            identity.disposition, identity.lat, identity.lon, identity.land_m2,
            cell_lat, cell_lon,
        ))
        self._conn.commit()

    def attach_listing(self, property_id: str, listing_id: str) -> None:
        stmt = "UPDATE listings SET property_id = ? WHERE id = ?"
        self._conn.execute(stmt, (property_id, listing_id))
        self._conn.commit()

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
        self._conn.commit()
