"""Tests for the SQLite connection setup and migration runner.

Run: python3 -m pytest tests/test_migrate.py -v
"""

import sqlite3

import pytest

from rentczecher.adapters.repositories.sqlite import connection, migrate

EXPECTED_TABLES = {
    "profiles", "properties", "property_images", "listings",
    "price_observations", "dedup_records", "notification_state", "scrape_runs",
}


class TestConnectionSetup:
    """Every connection opens with the pragmas the schema's integrity relies on."""

    def test_foreign_keys_are_enforced(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_journal_mode_is_wal(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"

    def test_busy_timeout_is_set(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


class TestMigrate:
    """apply_pending brings a fresh DB to the shipped schema, once, idempotently."""

    def test_fresh_db_gets_all_tables_at_version_1(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        assert migrate.apply_pending(conn) == [1]
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert EXPECTED_TABLES <= tables

    def test_second_run_is_a_noop(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        assert migrate.apply_pending(conn) == []

    def test_bad_source_is_rejected(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles VALUES ('p', 'P', 1, '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', '2026-08-02T00:00:00+00:00')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO listings VALUES "
                         "('idnes:1', 'x', 'p', 'idnes', 1, 'u', 't', 't', 't', 0)")

    def test_invalid_differences_json_is_rejected(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles VALUES ('p', 'P', 1, '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO listings VALUES "
                     "('sreality:1', 'x', 'p', 'sreality', 1, 'u', 't', 't', 't', 0)")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO dedup_records (property_id, listing_id, match_reason, differences, decided_at) "
                         "VALUES ('x', 'sreality:1', 'r', 'not json', 't')")

    def test_cascade_delete_removes_dependent_price_history(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles VALUES ('p', 'P', 1, '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO listings VALUES "
                     "('sreality:1', 'x', 'p', 'sreality', 1, 'u', 't', 't', 't', 0)")
        conn.execute("INSERT INTO price_observations (listing_id, price, observed_at) "
                     "VALUES ('sreality:1', 100, '2026-08-02T00:00:00+00:00')")
        conn.execute("DELETE FROM listings WHERE id = 'sreality:1'")
        assert conn.execute("SELECT count(*) FROM price_observations").fetchone()[0] == 0

    def test_mid_migration_failure_leaves_no_tables(self, tmp_path, monkeypatch):
        bad = tmp_path / "0001_bad.sql"
        bad.write_text("CREATE TABLE first_ok (id INTEGER PRIMARY KEY);\n"
                       "CREATE TABLE first_ok (id INTEGER PRIMARY KEY);\n")  # duplicate -> fails
        monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
        conn = connection.connect(tmp_path / "t.db")
        with pytest.raises(sqlite3.OperationalError):
            migrate.apply_pending(conn)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "first_ok" not in tables
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0

    def test_only_higher_numbered_migrations_apply(self, tmp_path, monkeypatch):
        (tmp_path / "0001_a.sql").write_text("CREATE TABLE a (id INTEGER PRIMARY KEY);\n")
        (tmp_path / "0002_b.sql").write_text("CREATE TABLE b (id INTEGER PRIMARY KEY);\n")
        monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
        conn = connection.connect(tmp_path / "t.db")
        conn.execute("PRAGMA user_version = 1")
        assert migrate.apply_pending(conn) == [2]
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "a" not in tables and "b" in tables

    def test_trailing_comment_after_last_statement_is_not_an_error(self, tmp_path, monkeypatch):
        (tmp_path / "0001_a.sql").write_text(
            "CREATE TABLE a (id INTEGER PRIMARY KEY);\n-- a closing note\n")
        monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
        conn = connection.connect(tmp_path / "t.db")
        assert migrate.apply_pending(conn) == [1]
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "a" in tables


class TestConcurrentWriters:
    """busy_timeout, not luck, lets a second writer wait out a held write lock."""

    def test_second_writer_waits_rather_than_erroring(self, tmp_path):
        db = tmp_path / "t.db"
        migrate.apply_pending(connection.connect(db))

        holder = connection.connect(db)
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("INSERT INTO profiles VALUES ('a', 'A', 1, '2026-08-02T00:00:00+00:00')")

        # A zero-timeout writer hits the held lock immediately: proves the lock
        # is real, so the waiting writer below is saved by the timeout, not luck.
        impatient = connection.connect(db)
        impatient.execute("PRAGMA busy_timeout = 0")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            impatient.execute("BEGIN IMMEDIATE")

        holder.commit()
        waiter = connection.connect(db)
        waiter.execute("INSERT INTO profiles VALUES ('b', 'B', 1, '2026-08-02T00:00:00+00:00')")
        waiter.commit()
        assert connection.connect(db).execute("SELECT count(*) FROM profiles").fetchone()[0] == 2
