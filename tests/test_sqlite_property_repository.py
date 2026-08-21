"""Behavior tests for the SQLite property repository, against a real temp-file DB.

The property repo is strictly mechanical: it persists decisions the dedup
algorithm already made (match reason, field divergences, which property a
listing attaches to). It never decides anything — that logic is the pipeline's.

Run: python3 -m pytest tests/test_sqlite_property_repository.py -v
"""

import sqlite3
from datetime import datetime, timezone

import pytest

from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.properties import SqlitePropertyRepository
from rentczecher.domain.geo import geocell
from rentczecher.domain.property import PropertyIdentity

BASE = datetime(2026, 8, 13, 6, 0, 0, tzinfo=timezone.utc)
CREATED = BASE.isoformat()


def _repo(tmp_path):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    conn.execute("INSERT INTO profiles VALUES ('p', 'P', 1, ?)", (CREATED,))
    conn.commit()
    return SqlitePropertyRepository(conn, now=lambda: BASE), conn


def _property(id="prop-1", **kw):
    return PropertyIdentity(id=id, created_at=CREATED, **kw)


def _seed_listing(conn, id="sreality:1", property_id="prop-1", profile_id="p"):
    conn.execute(
        "INSERT INTO listings (id, property_id, profile_id, source, url, "
        "first_seen_at, last_seen_at, scraped_at) VALUES (?, ?, ?, ?, 'u', ?, ?, ?)",
        (id, property_id, profile_id, id.split(":")[0], CREATED, CREATED, CREATED))
    conn.commit()


class TestCreateAndGet:
    def test_round_trips_canonical_facts(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.create(_property(title="Byt 2+kk", location="Praha 7", size_m2=55,
                              disposition="2+kk", lat=50.1, lon=14.4, land_m2=None))
        got = repo.get("prop-1")
        assert got.title == "Byt 2+kk"
        assert got.size_m2 == 55
        assert got.disposition == "2+kk"
        assert got.lat == 50.1

    def test_get_missing_returns_none(self, tmp_path):
        repo, _ = _repo(tmp_path)
        assert repo.get("nope") is None

    def test_created_at_is_tz_aware_utc(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.create(_property())
        ts = repo.get("prop-1").created_at
        assert ts.endswith("+00:00")
        assert datetime.fromisoformat(ts).tzinfo is not None


class TestGeocell:
    def test_created_property_with_coords_gets_its_cell(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.create(_property(lat=50.1, lon=14.4))
        cell_lat, cell_lon = conn.execute(
            "SELECT cell_lat, cell_lon FROM properties WHERE id = 'prop-1'").fetchone()
        assert (cell_lat, cell_lon) == geocell(50.1, 14.4)

    def test_created_property_without_coords_gets_null_cell(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.create(_property(lat=None, lon=None))
        cell_lat, cell_lon = conn.execute(
            "SELECT cell_lat, cell_lon FROM properties WHERE id = 'prop-1'").fetchone()
        assert (cell_lat, cell_lon) == (None, None)


class TestAttachListing:
    def test_points_a_listing_at_a_property(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.create(_property("prop-a"))
        repo.create(_property("prop-b"))
        _seed_listing(conn, id="sreality:1", property_id="prop-a")
        repo.attach_listing("prop-b", "sreality:1")
        assert conn.execute(
            "SELECT property_id FROM listings WHERE id = 'sreality:1'").fetchone()[0] == "prop-b"


class TestRecordDedup:
    def _seed(self, repo, conn):
        repo.create(_property("prop-1"))
        _seed_listing(conn)

    def test_records_match_reason_and_differences_as_json(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed(repo, conn)
        repo.record_dedup("prop-1", "sreality:1", "gps<200m",
                          {"size_m2": {"canonical": 55, "listing": 56}})
        reason, diffs = conn.execute(
            "SELECT match_reason, differences FROM dedup_records").fetchone()
        assert reason == "gps<200m"
        import json
        assert json.loads(diffs) == {"size_m2": {"canonical": 55, "listing": 56}}

    def test_null_differences_allowed(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed(repo, conn)
        repo.record_dedup("prop-1", "sreality:1", "exact")
        assert conn.execute("SELECT differences FROM dedup_records").fetchone()[0] is None

    def test_invalid_json_would_be_rejected_by_the_check(self, tmp_path):
        # The schema's json_valid CHECK is the last defense; prove it's live.
        repo, conn = _repo(tmp_path)
        self._seed(repo, conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO dedup_records (property_id, listing_id, match_reason, "
                         "differences, decided_at) VALUES ('prop-1', 'sreality:1', 'r', 'not json', ?)",
                         (CREATED,))

    def test_decided_at_is_tz_aware_utc(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed(repo, conn)
        repo.record_dedup("prop-1", "sreality:1", "gps<200m")
        ts = conn.execute("SELECT decided_at FROM dedup_records").fetchone()[0]
        assert ts.endswith("+00:00")


class TestCascade:
    def test_deleting_a_property_cascades_to_dedup_records(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.create(_property("prop-1"))
        _seed_listing(conn)
        repo.record_dedup("prop-1", "sreality:1", "gps<200m")
        conn.execute("DELETE FROM properties WHERE id = 'prop-1'")
        conn.commit()
        assert conn.execute("SELECT count(*) FROM dedup_records").fetchone()[0] == 0
