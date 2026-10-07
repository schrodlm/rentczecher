"""Tests for the SQLite connection setup and migration runner.

Run: python3 -m pytest tests/test_migrate.py -v
"""

import shutil
import sqlite3
from typing import get_args

import pytest

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.domain.disposition import ATYPICAL, Disposition
from rentczecher_engine.domain.location import PlaceKind
from rentczecher_engine.domain.profile import EstateType, OfferType, Portal

EXPECTED_TABLES = {
    "profiles", "properties", "property_images", "listings",
    "listing_tracking",
    "price_observations", "dedup_records", "scrape_runs",
    "portals", "offer_types", "estate_types", "place_kinds",
    "profile_criteria", "profile_portals", "profile_preferences",
    "preferred_dispositions", "preferred_places",
}


def _db_at_version(tmp_path, version):
    partial = tmp_path / "migrations"
    partial.mkdir()
    for path in migrate.MIGRATIONS_DIR.glob("*.sql"):
        if int(path.name.split("_")[0]) <= version:
            shutil.copy(path, partial / path.name)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(migrate, "MIGRATIONS_DIR", partial)
        conn = connection.connect(tmp_path / "t.db")
        assert migrate.apply_pending(conn)[-1] == version
    return conn


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

    def test_fresh_db_gets_all_tables_at_the_latest_version(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        assert migrate.apply_pending(conn) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 13
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert EXPECTED_TABLES <= tables

    def test_fresh_db_reaches_version_2_with_geocell_columns(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        columns = {r[1] for r in conn.execute("PRAGMA table_info(properties)")}
        assert {"cell_lat", "cell_lon"} <= columns

    def test_second_run_is_a_noop(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        assert migrate.apply_pending(conn) == []

    def test_bad_source_is_rejected(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', '2026-08-02T00:00:00+00:00')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO listings (id, property_id, source, url, scraped_at) "
                "VALUES ('idnes:1', 'x', 'idnes', 'u', 't')")

    def test_invalid_differences_json_is_rejected(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', '2026-08-02T00:00:00+00:00')")
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES ('sreality:1', 'x', 'sreality', 'u', 't')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO dedup_records (property_id, listing_id, match_reason, differences, decided_at) "
                         "VALUES ('x', 'sreality:1', 'r', 'not json', 't')")

    def test_cascade_delete_removes_dependent_price_history(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', '2026-08-02T00:00:00+00:00')")
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', '2026-08-02T00:00:00+00:00')")
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES ('sreality:1', 'x', 'sreality', 'u', 't')")
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


class TestDispositionsMigration:
    """The dispositions table holds the parser's vocabulary, and existing
    properties gain the code their raw text names."""

    def test_backfill_maps_raw_texts_to_disposition_codes(self, tmp_path):
        conn = _db_at_version(tmp_path, 9)
        raw_texts = {"layout": "2+KK", "studio": "Garsoniéra", "atypical": "Atypický",
                     "building": "Rodinný", "missing": None}
        for property_id, raw_text in raw_texts.items():
            conn.execute(
                "INSERT INTO properties (id, created_at, disposition_raw_text) VALUES (?, ?, ?)",
                (property_id, "2026-08-02T00:00:00+00:00", raw_text))
        conn.commit()
        assert migrate.apply_pending(conn)[0] == 10
        codes = dict(conn.execute("SELECT id, disposition_code FROM properties").fetchall())
        assert codes == {"layout": "2+kk", "studio": "1+kk", "atypical": "atypicky",
                         "building": None, "missing": None}

    def test_seeded_codes_are_exactly_the_parseable_dispositions(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        parseable = {ATYPICAL.code: ATYPICAL}
        for rooms in range(1, 10):
            for kitchen in ("kitchenette", "separate"):
                disposition = Disposition(rooms=rooms, kitchen=kitchen)
                parseable[disposition.code] = disposition
        seeded = {row[0]: Disposition(rooms=row[1], kitchen=row[2])
                  for row in conn.execute("SELECT code, rooms, kitchen FROM dispositions")}
        assert seeded == parseable


class TestProfilesMigration:
    """Profiles gain their criteria and preferences tables, earlier profile
    rows go with their tracking, and the lookups hold the engine's
    vocabularies."""

    NOW = "2026-10-04T00:00:00+00:00"

    VALID_CRITERIA = {
        "profile_id": "p", "offer_type": "rent", "estate_type": "flat", "place_kind": "obvod",
        "place_code": 78, "min_price": 1, "max_price": 2, "min_size_m2": 1, "max_size_m2": 1, "min_land_m2": 1,
    }
    INSERT_CRITERIA = """
        INSERT INTO profile_criteria
            (profile_id, offer_type, estate_type, place_kind, place_code, min_price, max_price,
             min_size_m2, max_size_m2, min_land_m2)
        VALUES (:profile_id, :offer_type, :estate_type, :place_kind, :place_code, :min_price, :max_price,
                :min_size_m2, :max_size_m2, :min_land_m2)
    """

    VALID_PREFERENCES = {
        "profile_id": "p", "price_per_m2_weight": 10, "disposition_weight": 10, "size_weight": 10,
        "ideal_size_m2": 55, "place_weight": 10, "land_weight": 10, "ideal_land_m2": 900,
        "price_weight": 10, "max_good_price": 4000000,
    }
    INSERT_PREFERENCES = """
        INSERT INTO profile_preferences
            (profile_id, price_per_m2_weight, disposition_weight, size_weight, ideal_size_m2,
             place_weight, land_weight, ideal_land_m2, price_weight, max_good_price)
        VALUES (:profile_id, :price_per_m2_weight, :disposition_weight, :size_weight, :ideal_size_m2,
                :place_weight, :land_weight, :ideal_land_m2, :price_weight, :max_good_price)
    """

    def _migrated_with_profile(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (self.NOW,))
        return conn

    def test_lookups_hold_the_engine_vocabularies(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        assert {row[0] for row in conn.execute("SELECT name FROM portals")} == set(get_args(Portal))
        assert {row[0] for row in conn.execute("SELECT name FROM offer_types")} == set(get_args(OfferType))
        assert {row[0] for row in conn.execute("SELECT name FROM estate_types")} == set(get_args(EstateType))
        assert {row[0] for row in conn.execute("SELECT name FROM place_kinds")} == set(get_args(PlaceKind))

    def test_earlier_profiles_go_with_their_tracking_and_listings_stay(self, tmp_path):
        conn = _db_at_version(tmp_path, 10)
        conn.execute("INSERT INTO profiles (id, name, active, created_at) VALUES ('old', 'Old', 1, ?)",
                     (self.NOW,))
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', ?)", (self.NOW,))
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES ('sreality:1', 'x', 'sreality', 'u', ?)", (self.NOW,))
        conn.execute("INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, last_seen_at) "
                     "VALUES ('old', 'sreality:1', ?, ?)", (self.NOW, self.NOW))
        conn.commit()
        assert migrate.apply_pending(conn) == [11, 12, 13]
        assert conn.execute("SELECT count(*) FROM profiles").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM listing_tracking").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM listings").fetchone()[0] == 1

    def test_a_full_valid_profile_is_accepted(self, tmp_path):
        conn = self._migrated_with_profile(tmp_path)
        conn.execute(self.INSERT_CRITERIA, self.VALID_CRITERIA)
        conn.execute(self.INSERT_PREFERENCES, self.VALID_PREFERENCES)
        conn.execute("INSERT INTO profile_portals (profile_id, portal) VALUES ('p', 'sreality')")
        conn.execute("INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '2+kk', 1)")
        conn.execute("INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) "
                     "VALUES ('p', 'cast_obce', 490024, 1)")

    @pytest.mark.parametrize("column, value", [
        ("min_price", 0), ("max_price", -1), ("min_size_m2", 0), ("max_size_m2", 0), ("min_land_m2", 0),
        ("offer_type", "lease"), ("estate_type", "garage"), ("place_kind", "street"),
    ])
    def test_criteria_reject_an_out_of_range_value(self, tmp_path, column, value):
        conn = self._migrated_with_profile(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(self.INSERT_CRITERIA, {**self.VALID_CRITERIA, column: value})

    @pytest.mark.parametrize("low, high", [
        ("min_price", "max_price"), ("min_size_m2", "max_size_m2"),
    ])
    def test_criteria_reject_a_range_running_backwards(self, tmp_path, low, high):
        conn = self._migrated_with_profile(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(self.INSERT_CRITERIA, {**self.VALID_CRITERIA, low: 3, high: 2})

    @pytest.mark.parametrize("setting", ["ideal_size_m2", "ideal_land_m2", "max_good_price"])
    @pytest.mark.parametrize("setting_value", [None, 0])
    def test_a_weighted_preference_needs_a_positive_setting(self, tmp_path, setting, setting_value):
        conn = self._migrated_with_profile(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(self.INSERT_PREFERENCES, {**self.VALID_PREFERENCES, setting: setting_value})

    def test_a_paused_profile_records_when_it_was_paused(self, tmp_path):
        conn = self._migrated_with_profile(tmp_path)
        conn.execute("UPDATE profiles SET paused_at = ? WHERE id = 'p'", (self.NOW,))
        assert conn.execute("SELECT paused_at FROM profiles").fetchone()[0] == self.NOW
        columns = {row[1] for row in conn.execute("PRAGMA table_info(profiles)")}
        assert "active" not in columns

    def test_deleting_a_profile_deletes_its_own_rows(self, tmp_path):
        conn = self._migrated_with_profile(tmp_path)
        conn.execute(self.INSERT_CRITERIA, self.VALID_CRITERIA)
        conn.execute(self.INSERT_PREFERENCES, self.VALID_PREFERENCES)
        conn.execute("INSERT INTO profile_portals (profile_id, portal) VALUES ('p', 'sreality')")
        conn.execute("INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '2+kk', 1)")
        conn.execute("INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) "
                     "VALUES ('p', 'cast_obce', 490024, 1)")
        conn.execute("DELETE FROM profiles WHERE id = 'p'")
        for table in ("profile_criteria", "profile_preferences", "profile_portals",
                      "preferred_dispositions", "preferred_places"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0, table

    @pytest.mark.parametrize("stmt", [
        "INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '3+kk', 1)",
        "INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) VALUES ('p', 'obvod', 78, 1)",
    ])
    def test_a_rank_is_unique_within_a_profile(self, tmp_path, stmt):
        conn = self._migrated_with_profile(tmp_path)
        conn.execute("INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '2+kk', 1)")
        conn.execute("INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) "
                     "VALUES ('p', 'cast_obce', 490024, 1)")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(stmt)

    @pytest.mark.parametrize("stmt", [
        "INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '2+kk', 0)",
        "INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) VALUES ('p', 'obvod', 78, 0)",
    ])
    def test_a_rank_starts_at_one(self, tmp_path, stmt):
        conn = self._migrated_with_profile(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(stmt)

    @pytest.mark.parametrize("stmt", [
        "INSERT INTO preferred_places (profile_id, place_kind, place_code, rank) VALUES ('p', 'street', 1, 1)",
        "INSERT INTO profile_portals (profile_id, portal) VALUES ('p', 'idnes')",
        "INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '10+kk', 1)",
    ])
    def test_an_unknown_place_kind_portal_or_disposition_is_rejected(self, tmp_path, stmt):
        conn = self._migrated_with_profile(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(stmt)


class TestAcceptedDispositionsMigration:
    """A profile's room range and kitchen kind become the dispositions they
    covered, and no range none, which accepts any."""

    NOW = "2026-10-07T00:00:00+00:00"

    def _accepted_after_migrating(self, tmp_path, min_rooms, max_rooms, kitchen):
        conn = _db_at_version(tmp_path, 12)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (self.NOW,))
        conn.execute(
            "INSERT INTO profile_criteria (profile_id, offer_type, estate_type, place_kind, place_code, "
            "min_rooms, max_rooms, kitchen) VALUES ('p', 'rent', 'flat', 'obvod', 78, ?, ?, ?)",
            (min_rooms, max_rooms, kitchen))
        conn.commit()
        assert migrate.apply_pending(conn) == [13]
        stmt = "SELECT disposition FROM accepted_dispositions WHERE profile_id = 'p' ORDER BY disposition"
        return [row[0] for row in conn.execute(stmt)]

    def test_a_range_with_a_kitchen_becomes_the_dispositions_it_covered(self, tmp_path):
        assert self._accepted_after_migrating(tmp_path, 2, 3, "kitchenette") == ["2+kk", "3+kk"]

    def test_a_range_without_a_kitchen_covers_both_kinds(self, tmp_path):
        assert self._accepted_after_migrating(tmp_path, 8, None, None) == ["8+1", "8+kk", "9+1", "9+kk"]

    def test_a_kitchen_alone_covers_every_room_count(self, tmp_path):
        assert self._accepted_after_migrating(tmp_path, None, None, "separate") == [
            "1+1", "2+1", "3+1", "4+1", "5+1", "6+1", "7+1", "8+1", "9+1"]

    def test_no_range_accepts_any_disposition(self, tmp_path):
        assert self._accepted_after_migrating(tmp_path, None, None, None) == []

    def test_the_search_keeps_its_other_bounds(self, tmp_path):
        conn = _db_at_version(tmp_path, 12)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (self.NOW,))
        conn.execute(
            "INSERT INTO profile_criteria (profile_id, offer_type, estate_type, place_kind, place_code, "
            "min_price, max_price, min_size_m2, max_size_m2, min_land_m2, min_rooms) "
            "VALUES ('p', 'sale', 'house', 'okres', 3401, 1, 2, 3, 4, 5, 2)")
        conn.commit()
        migrate.apply_pending(conn)
        row = conn.execute("SELECT * FROM profile_criteria").fetchone()
        assert tuple(row) == ("p", "sale", "house", "okres", 3401, 1, 2, 3, 4, 5)

    def test_an_unknown_disposition_is_refused(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (self.NOW,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO accepted_dispositions (profile_id, disposition) VALUES ('p', '2+2')")

    def test_deleting_a_profile_deletes_its_accepted_dispositions(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (self.NOW,))
        conn.execute("INSERT INTO accepted_dispositions (profile_id, disposition) VALUES ('p', '2+kk')")
        conn.execute("DELETE FROM profiles WHERE id = 'p'")
        assert conn.execute("SELECT count(*) FROM accepted_dispositions").fetchone()[0] == 0


class TestConcurrentWriters:
    """busy_timeout, not luck, lets a second writer wait out a held write lock."""

    def test_second_writer_waits_rather_than_erroring(self, tmp_path):
        db = tmp_path / "t.db"
        migrate.apply_pending(connection.connect(db))

        holder = connection.connect(db)
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("INSERT INTO profiles (id, name, created_at) VALUES ('a', 'A', '2026-08-02T00:00:00+00:00')")

        # A zero-timeout writer hits the held lock immediately: proves the lock
        # is real, so the waiting writer below is saved by the timeout, not luck.
        impatient = connection.connect(db)
        impatient.execute("PRAGMA busy_timeout = 0")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            impatient.execute("BEGIN IMMEDIATE")

        holder.commit()
        waiter = connection.connect(db)
        waiter.execute("INSERT INTO profiles (id, name, created_at) VALUES ('b', 'B', '2026-08-02T00:00:00+00:00')")
        waiter.commit()
        assert connection.connect(db).execute("SELECT count(*) FROM profiles").fetchone()[0] == 2


class TestPackaging:
    """The migration ships as package data, so db migrate works from an
    installed wheel and not only an editable checkout."""

    def test_migration_is_discoverable_as_package_data(self):
        from importlib.resources import files
        sql = files("rentczecher_engine.adapters.repositories.sqlite") / "migrations" / "0001_init.sql"
        assert sql.is_file()
        assert "CREATE TABLE properties" in sql.read_text()
