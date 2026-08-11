"""Behavior tests for the SQLite listing repository, against a real temp-file DB.

Pins the thresholds carried over from the legacy JSON store — the >=3-miss /
recently-first-seen disappearance rule and the 90-day prune — plus the new
append-only price stream that replaces the legacy single-value overwrite.
(Facts and price-drop detection moved to the property repo and the pipeline.)

Run: python3 -m pytest tests/test_sqlite_listing_repository.py -v
"""

from datetime import datetime, timedelta, timezone


from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.listings import SqliteListingRepository
from rentczecher.adapters.scrapers.base import Listing

PROFILE = "praha7-byty"
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
    conn.execute("INSERT INTO profiles VALUES (?, 'P', 1, ?)", (PROFILE, BASE.isoformat()))
    conn.execute("INSERT INTO properties (id, created_at) VALUES (?, ?)",
                 (PROPERTY, BASE.isoformat()))
    conn.commit()
    return SqliteListingRepository(conn, now=now or (lambda: BASE)), conn


def _listing(id="sreality:1", price=20000, **kw):
    return Listing.build(id=id, source=id.split(":")[0], title="t", price=price,
                         location="l", url="u", **kw)


class TestUpsert:
    def test_first_observation_inserts_listing_and_price(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        row = conn.execute("SELECT property_id, profile_id, source, active, miss_count "
                           "FROM listings WHERE id = 'sreality:1'").fetchone()
        assert tuple(row) == (PROPERTY, PROFILE, "sreality", 1, 0)
        assert repo.price_history("sreality:1")[0].price == 20000

    def test_first_seen_at_is_set_once(self, tmp_path):
        repo, conn = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=3)))
        repo.upsert(PROFILE, PROPERTY, _listing())
        repo.upsert(PROFILE, PROPERTY, _listing())
        first, last = conn.execute(
            "SELECT first_seen_at, last_seen_at FROM listings WHERE id = 'sreality:1'").fetchone()
        assert first == BASE.isoformat()
        assert last == (BASE + timedelta(hours=3)).isoformat()

    def test_re_observation_appends_a_second_price(self, tmp_path):
        repo, _ = _repo(tmp_path, now=_clock(BASE, BASE + timedelta(hours=3)))
        repo.upsert(PROFILE, PROPERTY, _listing(price=20000))
        repo.upsert(PROFILE, PROPERTY, _listing(price=19000))
        prices = [o.price for o in repo.price_history("sreality:1")]
        assert prices == [20000, 19000]


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
        counts = dict(conn.execute("SELECT id, miss_count FROM listings"))
        assert counts == {"sreality:1": 0, "sreality:2": 1}

    def test_absent_listing_is_marked_inactive(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        repo.increment_miss_counts(PROFILE, set())
        assert conn.execute("SELECT active FROM listings WHERE id = 'sreality:1'").fetchone()[0] == 0


class TestDisappeared:
    def _seed_missing(self, repo, conn, first_seen, miss_count):
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:9"))
        conn.execute("UPDATE listings SET first_seen_at = ?, miss_count = ? WHERE id = 'sreality:9'",
                     (first_seen.isoformat(), miss_count))
        conn.commit()

    def test_recently_first_seen_disappears(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=6), 3)
        assert [d["id"] for d in repo.get_disappeared(PROFILE, set())] == ["sreality:9"]

    def test_first_seen_before_window_is_excluded(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=8), 3)
        assert repo.get_disappeared(PROFILE, set()) == []

    def test_threshold_is_three_misses(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 2)
        assert repo.get_disappeared(PROFILE, set()) == []
        conn.execute("UPDATE listings SET miss_count = 3 WHERE id = 'sreality:9'")
        conn.commit()
        assert [d["id"] for d in repo.get_disappeared(PROFILE, set())] == ["sreality:9"]

    def test_still_present_is_not_disappeared(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 5)
        assert repo.get_disappeared(PROFILE, {"sreality:9"}) == []

    def test_carries_the_listing_url_and_source(self, tmp_path):
        repo, conn = _repo(tmp_path)
        self._seed_missing(repo, conn, BASE - timedelta(days=1), 3)
        (gone,) = repo.get_disappeared(PROFILE, set())
        assert gone["source"] == "sreality"
        assert gone["url"] == "u"


class TestPrune:
    def test_removes_listings_older_than_ninety_days(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:old"))
        conn.execute("UPDATE listings SET last_seen_at = ? WHERE id = 'sreality:old'",
                     ((BASE - timedelta(days=91)).isoformat(),))
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:new"))
        conn.commit()
        assert repo.prune(PROFILE) == 1
        assert repo.seen_ids(PROFILE) == {"sreality:new"}

    def test_boundary_keeps_exactly_ninety_days(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing(id="sreality:1"))
        conn.execute("UPDATE listings SET last_seen_at = ? WHERE id = 'sreality:1'",
                     ((BASE - timedelta(days=89)).isoformat(),))
        conn.commit()
        assert repo.prune(PROFILE) == 0


class TestTimestamps:
    def test_written_timestamps_are_tz_aware_utc(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.upsert(PROFILE, PROPERTY, _listing())
        for column in ("first_seen_at", "last_seen_at", "scraped_at"):
            ts = conn.execute(f"SELECT {column} FROM listings WHERE id = 'sreality:1'").fetchone()[0]
            assert ts.endswith("+00:00")
            assert datetime.fromisoformat(ts).tzinfo is not None
        obs_ts = repo.price_history("sreality:1")[0].observed_at
        assert obs_ts.endswith("+00:00")


class TestScrapedAt:
    def test_scraper_provided_scraped_at_is_stored(self, tmp_path):
        repo, conn = _repo(tmp_path)
        stamped = (BASE - timedelta(minutes=5)).isoformat()
        repo.upsert(PROFILE, PROPERTY, _listing(scraped_at=stamped))
        assert conn.execute(
            "SELECT scraped_at FROM listings WHERE id = 'sreality:1'").fetchone()[0] == stamped
