"""Tests for SqliteRunStore's persist.

Pins that persist_outcome writes the listing upserts and the miss-count
increments in one transaction: nothing lands if any step raises, so a
failed persist can never advance a miss counter on its own. Also pins
that a property keeps the most detailed location its postings gave.

Run: python3 -m pytest tests/test_sqlite_run_store.py -v
"""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.domain.dedup import DedupOutcome, MatchBand, MatchScore, MergeDecision
from rentczecher_engine.domain.location import Location, Place

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


PRAHA = Location(
    kraj=Place(code=19, name="Hlavní město Praha", lat=50.08, lon=14.42),
    okres=None,
    obec=Place(code=554782, name="Praha", lat=50.08, lon=14.42),
    obvod=None,
    mestska_cast=None,
    cast_obce=None,
    ulice=None,
    cislo_popisne=None,
    cislo_orientacni=None,
)
PRISTAVNI = Place(code=467103, name="Přístavní", lat=50.104, lon=14.452)


def _stored_ulice(conn, listing_id):
    stmt = """
        SELECT property_locations.ulice_code AS ulice_code FROM listings
        JOIN property_locations ON property_locations.property_id = listings.property_id
        WHERE listings.id = ?
    """
    row = conn.execute(stmt, (listing_id,)).fetchone()
    return row["ulice_code"] if row else None


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


class TestInboxListings:
    def test_reflects_persisted_and_viewed_state(self, tmp_path):
        store, conn = _store(tmp_path)
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"})
        store.mark_viewed(PROFILE_ID, "sreality:1")
        (card,) = store.inbox_listings(PROFILE_ID)
        assert card.id == "sreality:1"
        assert card.viewed_at == BASE.isoformat()

    def test_only_new_excludes_the_viewed_listing(self, tmp_path):
        store, conn = _store(tmp_path)
        store.persist_outcome(PROFILE_ID, "P", _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"})
        store.mark_viewed(PROFILE_ID, "sreality:1")
        assert store.inbox_listings(PROFILE_ID, only_new=True) == []


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


class TestPropertyLocation:
    def test_a_new_property_takes_its_postings_location(self, tmp_path):
        store, conn = _store(tmp_path)
        listing = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        store.persist_outcome(PROFILE_ID, "P", _outcome(listing), {}, current_ids={listing.id})
        assert _stored_ulice(conn, listing.id) == PRISTAVNI.code

    def test_a_coarser_posting_never_coarsens_the_stored_location(self, tmp_path):
        store, conn = _store(tmp_path)
        detailed = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        store.persist_outcome(PROFILE_ID, "P", _outcome(detailed), {}, current_ids={detailed.id})
        coarse = _listing(resolved_location=PRAHA)
        store.persist_outcome(PROFILE_ID, "P", _outcome(coarse), {}, current_ids={coarse.id})
        assert _stored_ulice(conn, detailed.id) == PRISTAVNI.code

    def test_a_more_detailed_posting_refines_the_stored_location(self, tmp_path):
        store, conn = _store(tmp_path)
        coarse = _listing(resolved_location=PRAHA)
        store.persist_outcome(PROFILE_ID, "P", _outcome(coarse), {}, current_ids={coarse.id})
        detailed = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        store.persist_outcome(PROFILE_ID, "P", _outcome(detailed), {}, current_ids={detailed.id})
        assert _stored_ulice(conn, detailed.id) == PRISTAVNI.code

    def test_a_merge_keeps_the_absorbed_more_detailed_location(self, tmp_path):
        store, conn = _store(tmp_path)
        absorbed = _listing(id="bezrealitky:1", resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        keeper = _listing(id="sreality:1", resolved_location=PRAHA)
        store.persist_outcome(PROFILE_ID, "P", _outcome(absorbed), {}, current_ids={absorbed.id})
        store.persist_outcome(PROFILE_ID, "P", _outcome(keeper), {}, current_ids={keeper.id})
        # The detailed posting is gone by the run that merges the two.
        gone = _listing(id="bezrealitky:1")
        merge = MergeDecision(keeper_id=keeper.id, absorbed_id=gone.id,
                              score=MatchScore(total=60.0, factors=(), band=MatchBand.MATCH))
        store.persist_outcome(PROFILE_ID, "P", DedupOutcome(survivors=[keeper], merges=(merge,), uncertain=()),
                              {gone.id: gone}, current_ids={keeper.id, gone.id})
        assert _stored_ulice(conn, keeper.id) == PRISTAVNI.code
