import sqlite3
from collections.abc import Callable
from datetime import datetime

from rentczecher.adapters.repositories.sqlite.clock import utc_now


class SqliteProfileRepository:
    """The pipeline's minimal need: a profile row must exist before its
    listings can reference it. Full profile management (create, edit,
    pause) arrives with the GUI's profile store and will replace this."""

    def __init__(self, conn: sqlite3.Connection, *, now: Callable[[], datetime] = utc_now):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._now = now

    def ensure(self, profile_id: str, name: str) -> None:
        stmt = "SELECT id FROM profiles WHERE id = ?"
        existing = self._conn.execute(stmt, (profile_id,)).fetchone()
        if existing is not None:
            return
        insert = """
            INSERT INTO profiles (id, name, active, created_at)
            VALUES (?, ?, 1, ?)
        """
        self._conn.execute(insert, (profile_id, name, self._now().isoformat()))
        self._conn.commit()
