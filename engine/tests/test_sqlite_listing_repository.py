"""Behavior tests for the SQLite listing repository, against a real temp-file DB.

Pins the disappearance rule (three or more misses while recently first seen),
the 90-day tracking prune, the append-only price stream, and the split between
listing facts (global, one row per portal posting) and per-profile tracking.

Run: python3 -m pytest tests/test_sqlite_listing_repository.py -v
"""

from datetime import datetime, timedelta, timezone


from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.listings import SqliteListingRepository
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.domain.disposition import Disposition
from rentczecher_engine.domain.geo import GeoPoint

PROFILE = "praha7-byty"
OTHER_PROFILE = "letna-byty"
PROPERTY = "prop-1"
BASE = datetime(2026, 8, 11, 6, 0, 0, tzinfo=timezone.utc)


def _clock(*times):
    it = iter(times)
    last = [None]

    def now():
        try:
            last[0] = next(it)
        except StopIteration:
            pass
        return last[0]
    return now


def _repo(tmp_path, now=None):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    for profile_id in (PROFILE, OTHER_PROFILE):
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES (?, 'P', ?)",
                     (profile_id, BASE.isoformat()))
    conn.execute("INSERT INTO properties (id, created_at) VALUES (?, ?)",
                 (PROPERTY, BASE.isoformat()))
    conn.commit()
    return SqliteListingRepository(conn, now=now or (lambda: BASE)), conn


def _listing(id="sreality:1", price=20000, **kw):
    return Listing.build(id=id, source=id.split(":")[0], title="t", price=price,
                         location_raw_text="l", url="u", **kw)


def _index(conn, profile_id, property_id):
    stmt = "SELECT profile_index FROM property_tracking WHERE profile_id = ? AND property_id = ?"
    return conn.execute(stmt, (profile_id, property_id)).fetchone()["profile_index"]


class TestPropertyIndexes:
    def test_indexes_the_flats_in_the_order_the_profile_found_them(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-2', ?)", (BASE.isoformat(),))
        repo.upsert(PROFILE, PROPERTY, _listing("sreality:1"))
        repo.upsert(PROFILE, "prop-2", _listing("sreality:2"))
        assert (_index(conn, PROFILE, PROPERTY), _index(conn, PROFILE, "prop-2")) == (1, 2)

    def test_a_flat_found_again_keeps_its_index(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-2', ?)", (BASE.isoformat(),))
        repo.upsert(PROFILE, PROPERTY, _listing("sreality:1"))
        repo.upsert(PROFILE, PROPERTY, _listing("bezrealitky:1"))
        repo.upsert(PROFILE, "prop-2", _listing("sreality:2"))
        assert (_index(conn, PROFILE, PROPERTY), _index(conn, PROFILE, "prop-2")) == (1, 2)

    def test_each_profile_counts_its_own_flats(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-2', ?)", (BASE.isoformat(),))
        repo.upsert(PROFILE, PROPERTY, _listing("sreality:1"))
        repo.upsert(PROFILE, "prop-2", _listing("sreality:2"))
        repo.upsert(OTHER_PROFILE, "prop-2", _listing("sreality:2"))
        assert _index(conn, OTHER_PROFILE, "prop-2") == 1


class TestUpsert:
    def test_first_observation_inserts_fact_tracking_and_price(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        fact = conn.execute("SELECT property_id, source FROM listings "
                            "WHERE id = 'sreality:1'").fetchone()
        assert tuple(fact) == (PROPERTY, "sreality")
        tracking = conn.execute(
            "SELECT miss_count FROM listing_tracking "
            "WHERE profile_id = ? AND listing_id = 'sreality:1'", (PROFILE,)).fetchone()
        assert tracking["miss_count"] == 0
        assert repo.price_history("sreality:1")[0].price == 20000

    def test_first_seen_at_is_set_once(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=3)))
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(PROFILE, PROPERTY, _listing())
        first, last = conn.execute(
            "SELECT first_seen_at, last_seen_at FROM listing_tracking "
            "WHERE profile_id = ? AND listing_id = 'sreality:1'", (PROFILE,)).fetchone()
        assert first == BASE.isoformat()
        assert last == (BASE + timedelta(hours=3)).isoformat()

    def test_re_observation_appends_a_second_price(self, tmp_path):
        repo, _ = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=3)))
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(price=19000))
        prices = [o.price for o in repo.price_history("sreality:1")]
        assert prices == [20000, 19000]

    def test_two_profiles_share_one_fact_row_with_separate_tracking(self, tmp_path):
        """The same portal posting seen by two profiles is one listing fact
        and two tracking rows: neither profile hides the listing from the
        other, and each tracks its own seen state."""
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing())
        assert conn.execute("SELECT count(*) FROM listings").fetchone()[0] == 1
        assert repo.seen_ids(PROFILE) == {"sreality:1"}
        assert repo.seen_ids(OTHER_PROFILE) == {"sreality:1"}

    def test_two_profiles_miss_counts_advance_independently(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing())
        repo.increment_miss_counts(PROFILE, set())
        counts = {
            row["profile_id"]: row["miss_count"]
            for row in conn.execute("SELECT profile_id, miss_count FROM listing_tracking")
        }
        assert counts == {PROFILE: 1, OTHER_PROFILE: 0}


class TestPriceHistory:
    def test_is_append_only(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=1)))
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(price=18000))
        assert conn.execute("SELECT count(*) FROM price_observations").fetchone()[0] == 2

    def test_direct_record_persists_across_a_reopen(self, tmp_path):
        # record_price_observation does not commit. The caller owns that
        # boundary, so this test stands in for one.
        from rentczecher_engine.domain.price import PriceObservation
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        repo.record_price_observation(PriceObservation(
            listing_id="sreality:1", price=17000, observed_at=BASE.isoformat()))
        conn.commit()
        conn.close()
        reopened = connection.connect(tmp_path / "t.db")
        assert reopened.execute(
            "SELECT count(*) FROM price_observations WHERE price = 17000").fetchone()[0] == 1


class TestPriceHistories:
    def test_lists_the_postings_by_portal_with_their_collapsed_prices(self, tmp_path):
        repo, _ = _repo(tmp_path, now=_clock(*(BASE + timedelta(hours=hour) for hour in range(4))))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1", price=21000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        postings = repo.price_histories(PROFILE, PROPERTY)
        assert postings is not None
        assert [posting.listing_id for posting in postings] == ["bezrealitky:1", "sreality:1"]
        bezrealitky, sreality = postings
        assert bezrealitky.source == "bezrealitky"
        assert [change.price for change in bezrealitky.changes] == [21000]
        assert [change.price for change in sreality.changes] == [20000, 19000]
        assert sreality.changes[0].first_seen_at == BASE.isoformat()
        assert sreality.changes[0].last_seen_at == (BASE + timedelta(hours=2)).isoformat()

    def test_charts_only_the_listings_the_profile_tracks(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="remax:1", price=18000))
        postings = repo.price_histories(PROFILE, PROPERTY)
        assert [posting.listing_id for posting in postings] == ["sreality:1"]

    def test_is_none_for_a_listing_the_profile_does_not_track(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:1"))
        assert repo.price_histories(PROFILE, PROPERTY) is None
        assert repo.price_histories(PROFILE, "prop-unknown") is None


class TestMissCounts:
    def test_absent_increments_present_resets(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:2"))
        repo.increment_miss_counts(PROFILE, {"sreality:1"})  # :2 absent
        counts = dict(conn.execute(
            "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?",
            (PROFILE,)))
        assert counts == {"sreality:1": 0, "sreality:2": 1}


class TestMarkViewed:
    def test_sets_viewed_at(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_viewed(PROFILE, PROPERTY)
        row = conn.execute(
            "SELECT viewed_at FROM property_tracking "
            "WHERE profile_id = ? AND property_id = ?", (PROFILE, PROPERTY)).fetchone()
        assert row["viewed_at"] == BASE.isoformat()

    def test_does_not_overwrite_an_earlier_view(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=1), BASE + timedelta(hours=2)))
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_viewed(PROFILE, PROPERTY)
        repo.mark_viewed(PROFILE, PROPERTY)
        row = conn.execute(
            "SELECT viewed_at FROM property_tracking "
            "WHERE profile_id = ? AND property_id = ?", (PROFILE, PROPERTY)).fetchone()
        assert row["viewed_at"] == (BASE + timedelta(hours=1)).isoformat()

    def test_scoped_to_the_profile(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing())
        repo.mark_viewed(PROFILE, PROPERTY)
        other = conn.execute(
            "SELECT viewed_at FROM property_tracking "
            "WHERE profile_id = ? AND property_id = ?", (OTHER_PROFILE, PROPERTY)).fetchone()
        assert other["viewed_at"] is None

    def test_does_not_commit(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        conn.commit()
        repo.mark_viewed(PROFILE, PROPERTY)
        conn.rollback()
        row = conn.execute(
            "SELECT viewed_at FROM property_tracking "
            "WHERE profile_id = ? AND property_id = ?", (PROFILE, PROPERTY)).fetchone()
        assert row["viewed_at"] is None


class TestUpdates:
    @staticmethod
    def _updated_at(conn, profile_id=PROFILE):
        stmt = "SELECT updated_at FROM property_tracking WHERE profile_id = ? AND property_id = ?"
        return conn.execute(stmt, (profile_id, PROPERTY)).fetchone()["updated_at"]

    def test_marking_records_when_the_flat_changed(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_viewed(PROFILE, PROPERTY)
        repo.mark_updated(PROFILE, PROPERTY)
        assert self._updated_at(conn) == BASE.isoformat()

    def test_viewing_again_clears_the_update_and_keeps_the_first_view(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=1), BASE + timedelta(hours=2),
                                                BASE + timedelta(hours=3)))
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_viewed(PROFILE, PROPERTY)
        repo.mark_updated(PROFILE, PROPERTY)
        repo.mark_viewed(PROFILE, PROPERTY)
        assert self._updated_at(conn) is None
        row = conn.execute("SELECT viewed_at FROM property_tracking WHERE profile_id = ?", (PROFILE,)).fetchone()
        assert row["viewed_at"] == (BASE + timedelta(hours=1)).isoformat()

    def test_marking_is_scoped_to_the_profile(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing())
        repo.mark_updated(PROFILE, PROPERTY)
        assert self._updated_at(conn, OTHER_PROFILE) is None

    def test_viewed_ids_hold_every_listing_on_a_viewed_flat(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing("sreality:1"))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing("bezrealitky:1"))
        repo.mark_viewed(PROFILE, PROPERTY)
        assert repo.viewed_ids(PROFILE) == {"sreality:1", "bezrealitky:1"}
        assert repo.viewed_ids(OTHER_PROFILE) == set()


class TestFavourite:
    def _row(self, conn):
        return conn.execute(
            "SELECT favourited_at, viewed_at FROM property_tracking "
            "WHERE profile_id = ? AND property_id = ?", (PROFILE, PROPERTY)).fetchone()

    def test_marking_keeps_the_listing_and_views_it(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_favourite(PROFILE, PROPERTY)
        row = self._row(conn)
        assert (row["favourited_at"], row["viewed_at"]) == (BASE.isoformat(), BASE.isoformat())

    def test_marking_again_keeps_the_first_times(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=1), BASE + timedelta(hours=2)))
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_viewed(PROFILE, PROPERTY)
        repo.mark_favourite(PROFILE, PROPERTY)
        repo.mark_favourite(PROFILE, PROPERTY)
        row = self._row(conn)
        assert row["viewed_at"] == (BASE + timedelta(hours=1)).isoformat()
        assert row["favourited_at"] == (BASE + timedelta(hours=2)).isoformat()

    def test_clearing_leaves_the_listing_viewed(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.mark_favourite(PROFILE, PROPERTY)
        repo.clear_favourite(PROFILE, PROPERTY)
        row = self._row(conn)
        assert row["favourited_at"] is None
        assert row["viewed_at"] is not None

    def test_scoped_to_the_profile(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing())
        repo.mark_favourite(PROFILE, PROPERTY)
        other = conn.execute(
            "SELECT favourited_at FROM property_tracking "
            "WHERE profile_id = ? AND property_id = ?", (OTHER_PROFILE, PROPERTY)).fetchone()
        assert other["favourited_at"] is None

    def test_does_not_commit(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        conn.commit()
        repo.mark_favourite(PROFILE, PROPERTY)
        conn.rollback()
        assert self._row(conn)["favourited_at"] is None


class TestTrackingAFlat:
    """Viewing and starring act on the flat, whichever of its listings the
    profile acts through."""

    def test_viewing_one_listing_views_the_flat_shown_by_another(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1", price=20000))
        repo.mark_viewed(PROFILE, PROPERTY)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.listing_id == "sreality:1"
        assert card.viewed_at == BASE.isoformat()

    def test_clearing_a_favourite_clears_the_whole_flat(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1", price=20000))
        repo.mark_favourite(PROFILE, PROPERTY)
        repo.clear_favourite(PROFILE, PROPERTY)
        (card,) = repo.tracked_properties(PROFILE)
        assert card.favourited_at is None
        assert card.viewed_at is not None

    def test_leaves_another_profiles_tracking_of_the_flat_alone(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.mark_favourite(PROFILE, PROPERTY)
        (other,) = repo.tracked_properties(OTHER_PROFILE)
        assert (other.viewed_at, other.favourited_at) == (None, None)

    def test_pruning_forgets_a_flat_with_no_tracked_listing_left(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.mark_viewed(PROFILE, PROPERTY)
        conn.execute("UPDATE listing_tracking SET last_seen_at = ?", ((BASE - timedelta(days=91)).isoformat(),))
        assert repo.prune(PROFILE) == 1
        assert conn.execute("SELECT count(*) FROM property_tracking WHERE profile_id = ?", (PROFILE,)).fetchone()[0] == 0


class TestPendingDisappeared:
    """A listing disappears when it is absent from a run, was first seen
    within the window, and reaches three misses counting that run."""

    def _seed_missing(self, repo, conn, first_seen, miss_count):
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:9"))
        conn.execute(
            "UPDATE listing_tracking SET first_seen_at = ?, miss_count = ? "
            "WHERE profile_id = ? AND listing_id = 'sreality:9'",
            (first_seen.isoformat(), miss_count, PROFILE))
        conn.commit()

    def test_absent_listing_one_miss_from_threshold_is_reported(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=6), 2)
        assert repo.pending_disappeared(PROFILE, set()) == {"sreality:9"}

    def test_absent_listing_still_short_of_threshold_is_not_reported(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 1)
        assert repo.pending_disappeared(PROFILE, set()) == set()

    def test_present_listing_is_never_reported_even_at_a_stale_miss_count(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 5)
        assert repo.pending_disappeared(PROFILE, {"sreality:9"}) == set()

    def test_first_seen_before_window_is_excluded_even_one_miss_from_threshold(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=8), 2)
        assert repo.pending_disappeared(PROFILE, set()) == set()

    def test_only_the_missing_profile_reports_it(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 2)
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:9"))
        assert repo.pending_disappeared(PROFILE, set()) == {"sreality:9"}
        assert repo.pending_disappeared(OTHER_PROFILE, set()) == set()

    def test_does_not_write_anything(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 2)
        repo.pending_disappeared(PROFILE, set())
        row = conn.execute(
            "SELECT miss_count FROM listing_tracking WHERE listing_id = 'sreality:9'").fetchone()
        assert row["miss_count"] == 2


class TestLatestPrices:
    def test_latest_observation_wins(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=100))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=90))
        assert repo.latest_prices(PROFILE) == {"sreality:1": 90}

    def test_listing_without_observation_is_absent(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES ('sreality:bare', ?, 'sreality', 'u', 't')", (PROPERTY,))
        conn.execute(
            "INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, "
            "last_seen_at, miss_count) VALUES (?, 'sreality:bare', 't', 't', 0)",
            (PROFILE,))
        conn.commit()
        assert repo.latest_prices(PROFILE) == {}

    def test_scoped_to_the_profile(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:mine", price=100))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:theirs", price=200))
        assert repo.latest_prices(PROFILE) == {"sreality:mine": 100}

    def test_is_the_price_the_profiles_own_scans_last_saw(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=1), BASE + timedelta(hours=2)))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=100))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:1", price=90))
        assert repo.latest_prices(PROFILE) == {"sreality:1": 100}
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=90))
        assert repo.latest_prices(PROFILE) == {"sreality:1": 90}


class TestPropertyIdOf:
    def test_returns_the_listing_property(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        assert repo.property_id_of("sreality:1") == PROPERTY

    def test_unknown_listing_is_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        assert repo.property_id_of("sreality:ghost") is None


class TestTrackedProperties:
    def test_carries_listing_and_property_facts(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("UPDATE properties SET title = ?, location_raw_text = ?, size_m2 = ?, land_m2 = ?, "
                     "disposition_raw_text = ? WHERE id = ?",
                     ("Byt 2+kk", "Praha 7", 55, 400, "2+kk", PROPERTY))
        conn.commit()
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.listing_id == "sreality:1"
        assert card.source == "sreality"
        assert card.url == "u"
        assert card.title == "Byt 2+kk"
        assert card.location_raw_text == "Praha 7"
        assert card.size_m2 == 55
        assert card.land_m2 == 400
        assert card.disposition_raw_text == "2+kk"

    def test_carries_the_property_disposition(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("UPDATE properties SET disposition_code = '3+1' WHERE id = ?", (PROPERTY,))
        conn.commit()
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.disposition == Disposition(rooms=3, kitchen="separate")

    def test_carries_the_property_point(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("UPDATE properties SET lat = 50.1029, lon = 14.4293 WHERE id = ?", (PROPERTY,))
        conn.commit()
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.point == GeoPoint(lat=50.1029, lon=14.4293)

    def test_missing_property_facts_are_none_not_dropped(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.title is None
        assert card.location_raw_text is None
        assert card.size_m2 is None
        assert card.land_m2 is None
        assert card.disposition_raw_text is None
        assert card.disposition is None
        assert card.point is None

    def test_carries_tracking_state(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        conn.execute(
            "UPDATE property_tracking SET favourited_at = ? "
            "WHERE profile_id = ? AND property_id = ?", (BASE.isoformat(), PROFILE, PROPERTY))
        conn.commit()
        repo.mark_viewed(PROFILE, PROPERTY)
        (card,) = repo.tracked_properties(PROFILE)
        assert card.first_seen_at == BASE.isoformat()
        assert card.viewed_at == BASE.isoformat()
        assert card.favourited_at == BASE.isoformat()

    def test_carries_when_a_scan_last_found_the_flat_changed(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.mark_viewed(PROFILE, PROPERTY)
        repo.mark_updated(PROFILE, PROPERTY)
        (card,) = repo.tracked_properties(PROFILE)
        assert card.updated_at == BASE.isoformat()

    def test_never_updated_is_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.updated_at is None

    def test_never_viewed_is_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.viewed_at is None

    def test_carries_the_latest_price(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price == 19000

    def test_no_price_observation_yet_is_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES ('sreality:1', ?, 'sreality', 'u', ?)", (PROPERTY, BASE.isoformat()))
        conn.execute(
            "INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, "
            "last_seen_at, miss_count) VALUES (?, 'sreality:1', ?, ?, 0)",
            (PROFILE, BASE.isoformat(), BASE.isoformat()))
        conn.execute("INSERT INTO property_tracking (profile_id, property_id) VALUES (?, ?)", (PROFILE, PROPERTY))
        conn.commit()
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price is None

    def test_price_drop_from_is_set_when_the_previous_price_was_higher(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price_drop_from == 20000

    def test_price_drop_from_survives_a_repeat_scan_at_the_dropped_price(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price_drop_from == 20000

    def test_price_drop_from_is_none_once_the_price_rises_back(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price_drop_from is None

    def test_price_drop_from_is_none_when_the_price_is_unchanged_or_up(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price_drop_from is None

    def test_price_drop_from_is_none_with_only_one_observation(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.price_drop_from is None

    def test_carries_sibling_sources_on_the_same_property(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.listing_id == "bezrealitky:1"
        assert [s.source for s in card.sibling_sources] == ["sreality"]
        assert card.sibling_sources[0].url == "u"

    def test_shows_a_flat_once_by_its_cheapest_listing(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1", price=19000))
        (card,) = repo.tracked_properties(PROFILE)
        assert (card.listing_id, card.price) == ("bezrealitky:1", 19000)
        assert [s.source for s in card.sibling_sources] == ["sreality"]

    def test_shows_the_first_found_of_equally_cheap_listings(self, tmp_path):
        repo, _ = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=1)))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1", price=20000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.listing_id == "sreality:1"
        assert card.first_seen_at == BASE.isoformat()

    def test_leaves_out_listings_only_another_profile_found(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=20000))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="remax:1", price=15000))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.listing_id == "sreality:1"
        assert card.sibling_sources == ()

    def test_a_flat_is_viewed_once_any_of_its_listings_is(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1", price=19000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="bezrealitky:1", price=20000))
        repo.mark_viewed(PROFILE, PROPERTY)
        (card,) = repo.tracked_properties(PROFILE)
        assert card.listing_id == "sreality:1"
        assert card.viewed_at is not None
        assert repo.tracked_properties(PROFILE, only_new=True) == []

    def test_no_siblings_is_an_empty_tuple(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        (card,) = repo.tracked_properties(PROFILE)
        assert card.sibling_sources == ()

    def test_only_new_excludes_viewed_listings(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('p2', ?)", (BASE.isoformat(),))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.upsert(PROFILE, "p2", _listing(id="sreality:2"))
        repo.mark_viewed(PROFILE, PROPERTY)
        cards = repo.tracked_properties(PROFILE, only_new=True)
        assert [card.listing_id for card in cards] == ["sreality:2"]

    def test_only_new_false_includes_viewed_listings(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.mark_viewed(PROFILE, PROPERTY)
        cards = repo.tracked_properties(PROFILE, only_new=False)
        assert [card.listing_id for card in cards] == ["sreality:1"]

    def test_scoped_to_the_profile(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:mine"))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:theirs"))
        cards = repo.tracked_properties(PROFILE)
        assert [card.listing_id for card in cards] == ["sreality:mine"]


class TestPrune:
    def test_forgets_tracking_older_than_ninety_days(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:old"))
        conn.execute("UPDATE listing_tracking SET last_seen_at = ? "
                     "WHERE listing_id = 'sreality:old'",
                     ((BASE - timedelta(days=91)).isoformat(),))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:new"))
        conn.commit()
        assert repo.prune(PROFILE) == 1
        assert repo.seen_ids(PROFILE) == {"sreality:new"}

    def test_boundary_keeps_exactly_ninety_days(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        conn.execute("UPDATE listing_tracking SET last_seen_at = ? "
                     "WHERE listing_id = 'sreality:1'",
                     ((BASE - timedelta(days=89)).isoformat(),))
        conn.commit()
        assert repo.prune(PROFILE) == 0

    def test_listing_facts_and_price_history_survive_pruning(self, tmp_path):
        """Pruning forgets only that the profile saw the listing. Deleting
        the posting and its price history is left to the property sweep."""
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:old"))
        conn.execute("UPDATE listing_tracking SET last_seen_at = ? "
                     "WHERE listing_id = 'sreality:old'",
                     ((BASE - timedelta(days=91)).isoformat(),))
        conn.commit()
        assert repo.prune(PROFILE) == 1
        assert conn.execute("SELECT count(*) FROM listings").fetchone()[0] == 1
        assert len(repo.price_history("sreality:old")) == 1

    def test_favourited_tracking_survives_pruning(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:kept"))
        stale = (BASE - timedelta(days=91)).isoformat()
        conn.execute("UPDATE listing_tracking SET last_seen_at = ? WHERE listing_id = 'sreality:kept'", (stale,))
        repo.mark_favourite(PROFILE, PROPERTY)
        conn.commit()
        assert repo.prune(PROFILE) == 0
        assert repo.seen_ids(PROFILE) == {"sreality:kept"}

    def test_scoped_to_the_profile(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:1"))
        conn.execute("UPDATE listing_tracking SET last_seen_at = ?",
                     ((BASE - timedelta(days=91)).isoformat(),))
        conn.commit()
        assert repo.prune(PROFILE) == 1
        assert repo.seen_ids(PROFILE) == set()
        assert repo.seen_ids(OTHER_PROFILE) == {"sreality:1"}


class TestTimestamps:
    def test_written_timestamps_are_tz_aware_utc(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        for column in ("first_seen_at", "last_seen_at"):
            ts = conn.execute(
                f"SELECT {column} FROM listing_tracking WHERE listing_id = 'sreality:1'"
            ).fetchone()[0]
            assert ts.endswith("+00:00")
            assert datetime.fromisoformat(ts).tzinfo is not None
        scraped = conn.execute(
            "SELECT scraped_at FROM listings WHERE id = 'sreality:1'").fetchone()[0]
        assert scraped.endswith("+00:00")
        obs_ts = repo.price_history("sreality:1")[0].observed_at
        assert obs_ts.endswith("+00:00")


class TestScrapedAt:
    def test_scraper_provided_scraped_at_is_stored(self, tmp_path):
        repo, conn = _repo(tmp_path)
        stamped = (BASE - timedelta(minutes=5)).isoformat()
        repo.upsert(PROFILE, PROPERTY, _listing(scraped_at=stamped))
        assert conn.execute(
            "SELECT scraped_at FROM listings WHERE id = 'sreality:1'").fetchone()[0] == stamped
