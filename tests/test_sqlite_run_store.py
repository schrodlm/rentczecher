"""Tests for SqliteRunStore's transactional persist.

Pins that persist_outcome writes the listing upserts and the miss-count
increments in one transaction: nothing lands if any step raises, so a
failed persist can never advance a miss counter on its own.

Run: python3 -m pytest tests/test_sqlite_run_store.py -v
"""

from datetime import datetime, timezone

import pytest

from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.dedup import DedupOutcome

PROFILE_ID = "praha7-byty"
BASE = datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)


def _store(tmp_path, now=None):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    return SqliteRunStore(conn, now=now or (lambda: BASE)), conn


def _listing(id="sreality:1", **kw):
    return Listing.build(id=id, source=id.split(":")[0], title="t", price=20000,
                         location="l", url="u", **kw)


def _outcome(*listings):
    return DedupOutcome(survivors=list(listings), merges=(), uncertain=())


class TestPersistOutcomeCommitsTogether:
    def test_upsert_and_miss_count_increment_land_in_one_transaction(self, tmp_path):
        store, conn = _store(tmp_path)
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"})
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids=set())  # :1 absent this run

        row = conn.execute(
            "SELECT miss_count FROM listing_tracking WHERE listing_id = 'sreality:1'").fetchone()
        assert row["miss_count"] == 1

    def test_persists_across_a_reopen(self, tmp_path):
        store, conn = _store(tmp_path)
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"})
        conn.close()

        reopened = connection.connect(tmp_path / "t.db")
        assert reopened.execute(
            "SELECT count(*) FROM listings WHERE id = 'sreality:1'").fetchone()[0] == 1


class TestMarkViewed:
    def test_commits_as_its_own_unit_of_work(self, tmp_path):
        store, conn = _store(tmp_path)
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"})
        store.mark_viewed(PROFILE_ID, "sreality:1")
        conn.close()

        reopened = connection.connect(tmp_path / "t.db")
        viewed_at = reopened.execute(
            "SELECT viewed_at FROM listing_tracking WHERE listing_id = 'sreality:1'"
        ).fetchone()[0]
        assert viewed_at == BASE.isoformat()


class TestPersistOutcomeRollsBackOnFailure:
    def test_a_failure_after_the_upsert_leaves_no_upsert_and_no_miss_count_change(self, tmp_path):
        store, conn = _store(tmp_path)
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"})
        before = dict(conn.execute(
            "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?",
            (PROFILE_ID,)))

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        # increment_miss_counts runs last in persist_outcome, so failing it
        # proves the upsert ahead of it did not commit alone.
        store._listings.increment_miss_counts = _boom
        with pytest.raises(RuntimeError):
            store.persist_outcome(
                PROFILE_ID, "P", _outcome(_listing(id="sreality:2")),
                {}, current_ids=set())

        after = dict(conn.execute(
            "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?",
            (PROFILE_ID,)))
        assert after == before
        assert conn.execute(
            "SELECT count(*) FROM listings WHERE id = 'sreality:2'").fetchone()[0] == 0
