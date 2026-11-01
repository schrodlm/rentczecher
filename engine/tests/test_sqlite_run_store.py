"""Tests for SqliteRunStore's persist.

Pins that persist_outcome writes the listing upserts and the miss-count
increments in one transaction: nothing lands if any step raises, so a
failed persist can never advance a miss counter on its own. Also pins
that a property keeps the most detailed location its postings gave, and
that a prune deletes the properties it leaves untracked.

Run: python3 -m pytest tests/test_sqlite_run_store.py -v
"""

from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.domain.dedup import DedupOutcome, MatchBand, MatchScore, MergeDecision
from rentczecher_engine.domain.location import Location, Place
from rentczecher_engine.domain.property import PropertyLocation
from tests.profiles import stored_profile

BASE = datetime(2026, 9, 19, 6, 0, 0, tzinfo=timezone.utc)


def _store(tmp_path, now=None):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    return SqliteRunStore(conn, now=now or (lambda: BASE)), conn


def _listing(id="sreality:1", **kw):
    return Listing.build(id=id, source=id.split(":")[0], title="t", price=20000,
                         location_raw_text="l", url="u", **kw)


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
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids=set(), updated_keeper_ids=set())  # :1 absent this run

        row = conn.execute(
            "SELECT miss_count FROM listing_tracking WHERE listing_id = 'sreality:1'").fetchone()
        assert row["miss_count"] == 1

    def test_persists_across_a_reopen(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        conn.close()

        reopened = connection.connect(tmp_path / "t.db")
        assert reopened.execute(
            "SELECT count(*) FROM listings WHERE id = 'sreality:1'").fetchone()[0] == 1


def _property_of(conn, listing_id):
    (property_id,) = conn.execute("SELECT property_id FROM listings WHERE id = ?", (listing_id,)).fetchone()
    return property_id


class TestPersistOutcomeRecordsGalleries:
    def test_records_a_new_listings_gallery(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        listing = _listing(id="sreality:1", photo_urls=("https://img.example/a.jpg", "https://img.example/b.jpg"))
        store.persist_outcome(profile_id, _outcome(listing), {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        stmt = "SELECT position, source_url FROM listing_photos ORDER BY position"
        assert [tuple(row) for row in conn.execute(stmt)] == [
            (0, "https://img.example/a.jpg"), (1, "https://img.example/b.jpg")]
        assert conn.execute("SELECT count(*) FROM advert_page_reads").fetchone()[0] == 0

    def test_records_that_a_listings_advert_page_holds_its_gallery(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        listing = _listing(id="remax:1", photo_urls=("https://img.example/a.jpg",), gallery_on_advert_page=True)
        store.persist_outcome(profile_id, _outcome(listing), {}, current_ids={"remax:1"}, updated_keeper_ids=set())
        stmt = "SELECT listing_id, read_at, attempts FROM advert_page_reads"
        assert [tuple(row) for row in conn.execute(stmt)] == [("remax:1", None, 0)]


class TestGalleryRequests:
    def _with_property(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")), {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        property_id = conn.execute("SELECT property_id FROM listings").fetchone()[0]
        return store, conn, profile_id, property_id

    def _requested(self, conn):
        return [row[0] for row in conn.execute("SELECT property_id FROM gallery_requests")]

    def test_a_request_is_committed(self, tmp_path):
        store, _, profile_id, property_id = self._with_property(tmp_path)
        assert store.request_gallery(profile_id, property_id)
        with closing(connection.connect(tmp_path / "t.db")) as other:
            assert self._requested(other) == [property_id]

    def test_a_flat_the_profile_does_not_track_is_refused(self, tmp_path):
        store, conn, profile_id, _ = self._with_property(tmp_path)
        assert not store.request_gallery(profile_id, "prop-unknown")
        assert self._requested(conn) == []


class TestPrune:
    def test_deletes_the_properties_the_prune_leaves_untracked(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")), {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        conn.execute("UPDATE listing_tracking SET last_seen_at = ?", ((BASE - timedelta(days=91)).isoformat(),))
        conn.commit()
        store.prune(profile_id)
        assert conn.execute("SELECT count(*) FROM properties").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM listings").fetchone()[0] == 0


class TestMarkViewed:
    def test_commits_as_its_own_unit_of_work(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        store.mark_viewed(profile_id, _property_of(conn, "sreality:1"))
        conn.close()

        reopened = connection.connect(tmp_path / "t.db")
        viewed_at = reopened.execute(
            "SELECT viewed_at FROM property_tracking "
            "JOIN listings ON listings.property_id = property_tracking.property_id "
            "WHERE listings.id = 'sreality:1'"
        ).fetchone()[0]
        assert viewed_at == BASE.isoformat()


class TestTrackedProperties:
    def test_reflects_persisted_and_viewed_state(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        store.mark_viewed(profile_id, _property_of(conn, "sreality:1"))
        (card,) = store.tracked_properties(profile_id)
        assert card.listing_id == "sreality:1"
        assert card.viewed_at == BASE.isoformat()

    def test_only_new_excludes_the_viewed_listing(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        store.mark_viewed(profile_id, _property_of(conn, "sreality:1"))
        assert store.tracked_properties(profile_id, only_new=True) == []

    def test_a_card_carries_the_stored_property_location(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        listing = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI, cislo_popisne="1401",
                                                     cislo_orientacni="5a"))
        store.persist_outcome(profile_id, _outcome(listing), {}, current_ids={listing.id}, updated_keeper_ids=set())
        (card,) = store.tracked_properties(profile_id)
        assert card.property_location == PropertyLocation(
            kraj_code=19,
            okres_code=None,
            obec_code=554782,
            obvod_code=None,
            mestska_cast_code=None,
            cast_obce_code=None,
            ulice_code=PRISTAVNI.code,
            cislo_popisne="1401",
            cislo_orientacni="5a",
        )

    def test_a_card_whose_property_has_no_location_carries_none(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        listing = _listing()
        store.persist_outcome(profile_id, _outcome(listing), {}, current_ids={listing.id}, updated_keeper_ids=set())
        (card,) = store.tracked_properties(profile_id)
        assert card.property_location is None


class TestPersistOutcomeRollsBackOnFailure:
    def test_a_failure_after_the_upsert_leaves_no_upsert_and_no_miss_count_change(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        store.persist_outcome(profile_id, _outcome(_listing(id="sreality:1")),
                              {}, current_ids={"sreality:1"}, updated_keeper_ids=set())
        before = dict(conn.execute(
            "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?",
            (profile_id,)))

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        # increment_miss_counts runs last in persist_outcome, so failing it
        # proves the upsert ahead of it did not commit alone.
        store._listings.increment_miss_counts = _boom
        with pytest.raises(RuntimeError):
            store.persist_outcome(
                profile_id, _outcome(_listing(id="sreality:2")),
                {}, current_ids=set(), updated_keeper_ids=set())

        after = dict(conn.execute(
            "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?",
            (profile_id,)))
        assert after == before
        assert conn.execute(
            "SELECT count(*) FROM listings WHERE id = 'sreality:2'").fetchone()[0] == 0


class TestPropertyLocation:
    def test_a_new_property_takes_its_postings_location(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        listing = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        store.persist_outcome(profile_id, _outcome(listing), {}, current_ids={listing.id}, updated_keeper_ids=set())
        assert _stored_ulice(conn, listing.id) == PRISTAVNI.code

    def test_a_coarser_posting_never_coarsens_the_stored_location(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        detailed = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        store.persist_outcome(profile_id, _outcome(detailed), {}, current_ids={detailed.id}, updated_keeper_ids=set())
        coarse = _listing(resolved_location=PRAHA)
        store.persist_outcome(profile_id, _outcome(coarse), {}, current_ids={coarse.id}, updated_keeper_ids=set())
        assert _stored_ulice(conn, detailed.id) == PRISTAVNI.code

    def test_a_more_detailed_posting_refines_the_stored_location(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        coarse = _listing(resolved_location=PRAHA)
        store.persist_outcome(profile_id, _outcome(coarse), {}, current_ids={coarse.id}, updated_keeper_ids=set())
        detailed = _listing(resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        store.persist_outcome(profile_id, _outcome(detailed), {}, current_ids={detailed.id}, updated_keeper_ids=set())
        assert _stored_ulice(conn, detailed.id) == PRISTAVNI.code

    def test_a_merge_keeps_the_absorbed_more_detailed_location(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        absorbed = _listing(id="bezrealitky:1", resolved_location=replace(PRAHA, ulice=PRISTAVNI))
        keeper = _listing(id="sreality:1", resolved_location=PRAHA)
        store.persist_outcome(profile_id, _outcome(absorbed), {}, current_ids={absorbed.id}, updated_keeper_ids=set())
        store.persist_outcome(profile_id, _outcome(keeper), {}, current_ids={keeper.id}, updated_keeper_ids=set())
        # The detailed posting is gone by the run that merges the two.
        gone = _listing(id="bezrealitky:1")
        merge = MergeDecision(keeper_id=keeper.id, absorbed_id=gone.id,
                              score=MatchScore(total=60.0, factors=(), band=MatchBand.MATCH))
        store.persist_outcome(profile_id, DedupOutcome(survivors=[keeper], merges=(merge,), uncertain=()),
                              {gone.id: gone}, current_ids={keeper.id, gone.id}, updated_keeper_ids=set())
        assert _stored_ulice(conn, keeper.id) == PRISTAVNI.code


class TestUpdatedFlats:
    def test_persist_marks_the_property_of_each_updated_keeper(self, tmp_path):
        store, conn = _store(tmp_path)
        profile_id = stored_profile(conn).id
        listing = _listing(id="sreality:1")
        store.persist_outcome(profile_id, _outcome(listing), {}, current_ids={listing.id}, updated_keeper_ids=set())
        conn.execute("UPDATE property_tracking SET viewed_at = ?", (BASE.isoformat(),))
        store.persist_outcome(profile_id, _outcome(listing), {},
                              current_ids={listing.id}, updated_keeper_ids={listing.id})
        assert conn.execute("SELECT updated_at FROM property_tracking").fetchone()[0] == BASE.isoformat()
