"""Behavior tests for the SQLite listing repository, against a real temp-file DB.

Pins the disappearance rule (three or more misses while recently first seen),
the 90-day tracking prune, the append-only price stream, and the split between
listing facts (global, one row per portal posting) and per-profile tracking.

Run: python3 -m pytest tests/test_sqlite_listing_repository.py -v
"""

from datetime import datetime, timedelta, timezone


from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.listings import SqliteListingRepository
from rentczecher.adapters.scrapers.base import Listing

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
        conn.execute("INSERT INTO profiles VALUES (?, 'P', 1, ?)",
                     (profile_id, BASE.isoformat()))
    conn.execute("INSERT INTO properties (id, created_at) VALUES (?, ?)",
                 (PROPERTY, BASE.isoformat()))
    conn.commit()
    return SqliteListingRepository(conn, now=now or (lambda: BASE)), conn


def _listing(id="sreality:1", price=20000, **kw):
    return Listing.build(id=id, source=id.split(":")[0], title="t", price=price,
                         location="l", url="u", **kw)


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
        # record_price_observation is public; a caller that isn't upsert must
        # still see its write committed after the connection closes.
        from rentczecher.domain.price import PriceObservation
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        repo.record_price_observation(PriceObservation(
            listing_id="sreality:1", price=17000, observed_at=BASE.isoformat()))
        conn.close()
        reopened = connection.connect(tmp_path / "t.db")
        assert reopened.execute(
            "SELECT count(*) FROM price_observations WHERE price = 17000").fetchone()[0] == 1


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


class TestDisappeared:
    def _seed_missing(self, repo, conn, first_seen, miss_count):
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:9"))
        conn.execute(
            "UPDATE listing_tracking SET first_seen_at = ?, miss_count = ? "
            "WHERE profile_id = ? AND listing_id = 'sreality:9'",
            (first_seen.isoformat(), miss_count, PROFILE))
        conn.commit()

    def test_recently_first_seen_disappears(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=6), 3)
        assert [d.id for d in repo.get_disappeared(PROFILE, set())] == ["sreality:9"]

    def test_first_seen_before_window_is_excluded(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=8), 3)
        assert repo.get_disappeared(PROFILE, set()) == []

    def test_threshold_is_three_misses(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 2)
        assert repo.get_disappeared(PROFILE, set()) == []
        conn.execute("UPDATE listing_tracking SET miss_count = 3 "
                     "WHERE listing_id = 'sreality:9'")
        conn.commit()
        assert [d.id for d in repo.get_disappeared(PROFILE, set())] == ["sreality:9"]

    def test_still_present_is_not_disappeared(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 5)
        assert repo.get_disappeared(PROFILE, {"sreality:9"}) == []

    def test_only_the_missing_profile_reports_it(self, tmp_path):
        """A listing another profile still tracks with zero misses is
        disappeared only for the profile that lost it."""
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 3)
        repo.upsert(OTHER_PROFILE, PROPERTY, _listing(id="sreality:9"))
        assert [d.id for d in repo.get_disappeared(PROFILE, set())] == ["sreality:9"]
        assert repo.get_disappeared(OTHER_PROFILE, set()) == []

    def test_carries_the_listing_url_and_source(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 3)
        (gone,) = repo.get_disappeared(PROFILE, set())
        assert gone.source == "sreality"
        assert gone.url == "u"

    def test_carries_the_property_title_and_location(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 3)
        conn.execute("UPDATE properties SET title = ?, location = ? WHERE id = ?",
                     ("Byt 2+kk", "Praha 7", PROPERTY))
        conn.commit()
        (gone,) = repo.get_disappeared(PROFILE, set())
        assert gone.title == "Byt 2+kk"
        assert gone.location == "Praha 7"

    def test_missing_title_is_none_not_dropped(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 3)
        (gone,) = repo.get_disappeared(PROFILE, set())
        assert gone.title is None
        assert gone.location is None

    def test_carries_the_latest_of_several_price_observations(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:9", price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:9", price=19000))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:9", price=18000))
        conn.execute(
            "UPDATE listing_tracking SET first_seen_at = ?, miss_count = ? "
            "WHERE listing_id = 'sreality:9'",
            ((BASE - timedelta(days=1)).isoformat(), 3))
        conn.commit()
        (gone,) = repo.get_disappeared(PROFILE, set())
        assert gone.price == 18000

    def test_no_price_observation_yet_is_none_not_dropped(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES ('sreality:9', ?, 'sreality', 'u', ?)",
            (PROPERTY, BASE.isoformat()))
        conn.execute(
            "INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, "
            "last_seen_at, miss_count) VALUES (?, 'sreality:9', ?, ?, 3)",
            (PROFILE, (BASE - timedelta(days=1)).isoformat(), BASE.isoformat()))
        conn.commit()
        (gone,) = repo.get_disappeared(PROFILE, set())
        assert gone.price is None


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


class TestPropertyIdOf:
    def test_returns_the_listing_property(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        assert repo.property_id_of("sreality:1") == PROPERTY

    def test_unknown_listing_is_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        assert repo.property_id_of("sreality:ghost") is None


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
        """Pruning forgets that the profile saw the listing. The posting
        itself and its price history stay as global history."""
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
        conn.execute(
            "UPDATE listing_tracking SET last_seen_at = ?, favourited_at = ? "
            "WHERE listing_id = 'sreality:kept'",
            (stale, BASE.isoformat()))
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
