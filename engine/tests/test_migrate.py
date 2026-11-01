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
    "profiles", "properties", "listing_photos", "listings",
    "listing_tracking", "property_tracking",
    "price_observations", "dedup_records", "scrape_runs",
    "portals", "offer_types", "estate_types", "place_kinds",
    "profile_criteria", "profile_portals", "profile_preferences",
    "preferred_dispositions", "preferred_places",
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

    def test_fresh_db_gets_all_tables_at_the_latest_version(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        assert migrate.apply_pending(conn) == [1, 2, 3, 4, 5]
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert EXPECTED_TABLES <= tables

    def test_properties_carry_their_geocell_columns(self, tmp_path):
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
                "VALUES ('no-such-portal:1', 'x', 'no-such-portal', 'u', 't')")

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


class TestForeignKeysDuringMigration:
    """A migration runs with foreign keys off, so it can rebuild a table, and
    commits only when it orphans no row that had its parent before."""

    PARENT_AND_CHILD = (
        "CREATE TABLE parent (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE child (id INTEGER PRIMARY KEY,"
        " parent_id INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE);\n"
        "INSERT INTO parent (id) VALUES (1);\n"
        "INSERT INTO child (id, parent_id) VALUES (10, 1);\n")

    def _migrated_to_parent_and_child(self, tmp_path, monkeypatch):
        (tmp_path / "0001_parent_and_child.sql").write_text(self.PARENT_AND_CHILD)
        monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        return conn

    def test_rebuilding_a_parent_table_keeps_its_child_rows(self, tmp_path, monkeypatch):
        conn = self._migrated_to_parent_and_child(tmp_path, monkeypatch)
        (tmp_path / "0002_rebuild_parent.sql").write_text(
            "CREATE TABLE parent_new (id INTEGER PRIMARY KEY, name TEXT);\n"
            "INSERT INTO parent_new (id) SELECT id FROM parent;\n"
            "DROP TABLE parent;\n"
            "ALTER TABLE parent_new RENAME TO parent;\n")
        assert migrate.apply_pending(conn) == [2]
        assert conn.execute("SELECT id, parent_id FROM child").fetchall() == [(10, 1)]

    def test_a_migration_that_orphans_rows_applies_nothing(self, tmp_path, monkeypatch):
        conn = self._migrated_to_parent_and_child(tmp_path, monkeypatch)
        (tmp_path / "0002_orphan_child.sql").write_text(
            "CREATE TABLE marker (id INTEGER PRIMARY KEY);\n"
            "DELETE FROM parent;\n")
        with pytest.raises(sqlite3.IntegrityError, match="child"):
            migrate.apply_pending(conn)
        assert conn.execute("SELECT id FROM parent").fetchall() == [(1,)]
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "marker" not in tables
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1

    def test_rows_orphaned_before_a_migration_do_not_block_it(self, tmp_path, monkeypatch):
        conn = self._migrated_to_parent_and_child(tmp_path, monkeypatch)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM parent")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        (tmp_path / "0002_marker.sql").write_text("CREATE TABLE marker (id INTEGER PRIMARY KEY);\n")
        assert migrate.apply_pending(conn) == [2]

    def test_foreign_keys_are_on_after_a_migration_applies(self, tmp_path, monkeypatch):
        conn = self._migrated_to_parent_and_child(tmp_path, monkeypatch)
        (tmp_path / "0002_marker.sql").write_text("CREATE TABLE marker (id INTEGER PRIMARY KEY);\n")
        assert migrate.apply_pending(conn) == [2]
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_foreign_keys_are_on_after_a_migration_is_refused(self, tmp_path, monkeypatch):
        conn = self._migrated_to_parent_and_child(tmp_path, monkeypatch)
        (tmp_path / "0002_orphan_child.sql").write_text("DELETE FROM parent;\n")
        with pytest.raises(sqlite3.IntegrityError):
            migrate.apply_pending(conn)
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


class TestPropertyIndexes:
    """Flats tracked before indexing get indexes in the order each profile
    found them."""

    def test_indexes_the_flats_already_tracked_in_the_order_found(self, tmp_path, monkeypatch):
        first_only = tmp_path / "first"
        first_only.mkdir()
        (first_only / "0001_init.sql").write_text((migrate.MIGRATIONS_DIR / "0001_init.sql").read_text())
        real = migrate.MIGRATIONS_DIR
        monkeypatch.setattr(migrate, "MIGRATIONS_DIR", first_only)
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        for profile_id in ("p", "q"):
            conn.execute("INSERT INTO profiles (id, name, created_at) VALUES (?, 'P', 't')", (profile_id,))
        for property_id in ("prop-c", "prop-a", "prop-b"):
            conn.execute("INSERT INTO properties (id, created_at) VALUES (?, 't')", (property_id,))
        for profile_id, property_id in (("p", "prop-c"), ("q", "prop-b"), ("p", "prop-a"), ("p", "prop-b")):
            conn.execute("INSERT INTO property_tracking (profile_id, property_id) VALUES (?, ?)",
                         (profile_id, property_id))
        conn.commit()
        monkeypatch.setattr(migrate, "MIGRATIONS_DIR", real)
        migrate.apply_pending(conn)
        stmt = "SELECT profile_id, property_id, profile_index FROM property_tracking ORDER BY profile_id, profile_index"
        assert [tuple(row) for row in conn.execute(stmt)] == [
            ("p", "prop-c", 1), ("p", "prop-a", 2), ("p", "prop-b", 3), ("q", "prop-b", 1)]


class TestDispositions:
    """The dispositions table holds the parser's vocabulary."""

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


class TestProfileTables:
    """The profile tables accept only valid profiles, and the lookups hold
    the engine's vocabularies."""

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
        "preferred_size_m2": 55, "place_weight": 10, "land_weight": 10, "preferred_land_m2": 900,
        "price_weight": 10, "preferred_price": 4000000,
    }
    INSERT_PREFERENCES = """
        INSERT INTO profile_preferences
            (profile_id, price_per_m2_weight, disposition_weight, size_weight, preferred_size_m2,
             place_weight, land_weight, preferred_land_m2, price_weight, preferred_price)
        VALUES (:profile_id, :price_per_m2_weight, :disposition_weight, :size_weight, :preferred_size_m2,
                :place_weight, :land_weight, :preferred_land_m2, :price_weight, :preferred_price)
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

    @pytest.mark.parametrize("setting", ["preferred_size_m2", "preferred_land_m2", "preferred_price"])
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
        "INSERT INTO profile_portals (profile_id, portal) VALUES ('p', 'no-such-portal')",
        "INSERT INTO preferred_dispositions (profile_id, disposition, rank) VALUES ('p', '10+kk', 1)",
    ])
    def test_an_unknown_place_kind_portal_or_disposition_is_rejected(self, tmp_path, stmt):
        conn = self._migrated_with_profile(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(stmt)


class TestAcceptedDispositions:
    """A profile accepts only dispositions the dispositions table holds, and
    they go with the profile."""

    NOW = "2026-10-07T00:00:00+00:00"

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


class TestListingPhotos:
    """A listing's photos sit at distinct positions, each stored file belongs
    to one photo, and the photos go with their listing."""

    NOW = "2026-10-20T00:00:00+00:00"

    def _with_listing(self, tmp_path):
        conn = connection.connect(tmp_path / "t.db")
        migrate.apply_pending(conn)
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', ?)", (self.NOW,))
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES ('sreality:1', 'x', 'sreality', 'u', ?)", (self.NOW,))
        return conn

    def test_a_position_holds_one_photo(self, tmp_path):
        conn = self._with_listing(tmp_path)
        conn.execute("INSERT INTO listing_photos (listing_id, position, source_url) VALUES ('sreality:1', 0, 'a')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO listing_photos (listing_id, position, source_url) VALUES ('sreality:1', 0, 'b')")

    def test_a_stored_file_belongs_to_one_photo(self, tmp_path):
        conn = self._with_listing(tmp_path)
        stmt = "INSERT INTO listing_photos (listing_id, position, source_url, file_key) VALUES ('sreality:1', ?, ?, 'k')"
        conn.execute(stmt, (0, "a"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(stmt, (1, "b"))

    @pytest.mark.parametrize("column", ["position", "attempts"])
    def test_a_count_is_never_negative(self, tmp_path, column):
        conn = self._with_listing(tmp_path)
        conn.execute("INSERT INTO listing_photos (listing_id, position, source_url) VALUES ('sreality:1', 0, 'a')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f"UPDATE listing_photos SET {column} = -1")

    def test_photos_go_with_their_listing(self, tmp_path):
        conn = self._with_listing(tmp_path)
        conn.execute("INSERT INTO listing_photos (listing_id, position, source_url) VALUES ('sreality:1', 0, 'a')")
        conn.execute("DELETE FROM listings WHERE id = 'sreality:1'")
        assert conn.execute("SELECT count(*) FROM listing_photos").fetchone()[0] == 0

    def test_an_advert_page_read_goes_with_its_listing(self, tmp_path):
        conn = self._with_listing(tmp_path)
        conn.execute("INSERT INTO advert_page_reads (listing_id) VALUES ('sreality:1')")
        conn.execute("DELETE FROM listings WHERE id = 'sreality:1'")
        assert conn.execute("SELECT count(*) FROM advert_page_reads").fetchone()[0] == 0


class TestListingPortalReference:
    """Upgrading a database to a listing source that references the portals
    table keeps every listing and everything read with it."""

    NOW = "2026-10-31T00:00:00+00:00"
    LISTING_CHILDREN = ("listing_tracking", "price_observations", "dedup_records",
                        "listing_photos", "advert_page_reads")

    def _at_version_2(self, tmp_path, monkeypatch):
        migrations = tmp_path / "migrations"
        migrations.mkdir()
        shutil.copy(migrate.MIGRATIONS_DIR / "0001_init.sql", migrations)
        shutil.copy(migrate.MIGRATIONS_DIR / "0002_listing_photos.sql", migrations)
        conn = connection.connect(tmp_path / "t.db")
        with monkeypatch.context() as patch:
            patch.setattr(migrate, "MIGRATIONS_DIR", migrations)
            migrate.apply_pending(conn)
        return conn

    def _add_listing_with_children(self, conn, listing_id):
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES (?, 'x', 'sreality', 'u', ?)", (listing_id, self.NOW))
        conn.execute("INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, last_seen_at) "
                     "VALUES ('p', ?, ?, ?)", (listing_id, self.NOW, self.NOW))
        conn.execute("INSERT INTO price_observations (listing_id, price, observed_at) VALUES (?, 100, ?)",
                     (listing_id, self.NOW))
        conn.execute("INSERT INTO dedup_records (property_id, listing_id, match_reason, decided_at) "
                     "VALUES ('x', ?, 'r', ?)", (listing_id, self.NOW))
        conn.execute("INSERT INTO listing_photos (listing_id, position, source_url) VALUES (?, 0, 'u')",
                     (listing_id,))
        conn.execute("INSERT INTO advert_page_reads (listing_id) VALUES (?)", (listing_id,))

    def _at_version_2_with_listings(self, tmp_path, monkeypatch):
        conn = self._at_version_2(tmp_path, monkeypatch)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (self.NOW,))
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('x', ?)", (self.NOW,))
        self._add_listing_with_children(conn, "sreality:1")
        self._add_listing_with_children(conn, "remax:2")
        conn.commit()
        return conn

    def _with_a_rowid_gap(self, tmp_path, monkeypatch):
        """A deleted first listing, so renumbering the rest would change them."""
        conn = self._at_version_2_with_listings(tmp_path, monkeypatch)
        conn.execute("DELETE FROM listings WHERE id = 'sreality:1'")
        conn.commit()
        return conn

    def _rows_by_table(self, conn):
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("listings", *self.LISTING_CHILDREN)}

    def test_every_listing_and_its_children_survive_the_upgrade(self, tmp_path, monkeypatch):
        conn = self._at_version_2_with_listings(tmp_path, monkeypatch)
        before = self._rows_by_table(conn)
        assert migrate.apply_pending(conn) == [3, 4, 5]
        assert self._rows_by_table(conn) == before

    def test_a_listing_keeps_its_rowid(self, tmp_path, monkeypatch):
        conn = self._with_a_rowid_gap(tmp_path, monkeypatch)
        before = conn.execute("SELECT rowid, id FROM listings").fetchall()
        migrate.apply_pending(conn)
        assert conn.execute("SELECT rowid, id FROM listings").fetchall() == before

    def test_a_listing_orphaned_before_the_upgrade_does_not_block_it(self, tmp_path, monkeypatch):
        conn = self._with_a_rowid_gap(tmp_path, monkeypatch)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES ('remax:3', 'gone', 'remax', 'u', ?)", (self.NOW,))
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        assert migrate.apply_pending(conn) == [3, 4, 5]

    def test_deleting_a_listing_still_deletes_its_children(self, tmp_path, monkeypatch):
        conn = self._at_version_2_with_listings(tmp_path, monkeypatch)
        migrate.apply_pending(conn)
        conn.execute("DELETE FROM listings WHERE id = 'sreality:1'")
        for table in self.LISTING_CHILDREN:
            assert conn.execute(f"SELECT count(*) FROM {table} WHERE listing_id = 'sreality:1'"
                                ).fetchone()[0] == 0, table


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
