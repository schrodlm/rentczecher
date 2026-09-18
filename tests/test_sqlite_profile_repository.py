"""Tests for the minimal profile row store.

Run: python3 -m pytest tests/test_sqlite_profile_repository.py -v
"""

from datetime import datetime, timezone

from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.profiles import SqliteProfileRepository

BASE = datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)


def _repo(tmp_path):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    return SqliteProfileRepository(conn, now=lambda: BASE), conn


class TestEnsure:
    def test_creates_the_row_once(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.ensure("praha7-byty", "Praha 7")
        repo.ensure("praha7-byty", "Praha 7")
        rows = conn.execute("SELECT id, name, active, created_at FROM profiles").fetchall()
        assert len(rows) == 1
        assert rows[0]["id"] == "praha7-byty"
        assert rows[0]["created_at"] == BASE.isoformat()

    def test_existing_row_is_left_untouched(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.ensure("praha7-byty", "Original")
        repo.ensure("praha7-byty", "Renamed")
        row = conn.execute("SELECT name FROM profiles WHERE id = 'praha7-byty'").fetchone()
        assert row["name"] == "Original"
