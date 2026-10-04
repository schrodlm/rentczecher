"""Tests for storing and reading profiles.

Run: python3 -m pytest tests/test_sqlite_profile_repository.py -v
"""

from datetime import datetime, timezone

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.profiles import SqliteProfileRepository
from rentczecher_engine.domain.location import PlaceRef
from tests.profiles import criteria, layouts, preferences

BASE = datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)

FULL_CRITERIA = criteria(
    offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401),
    min_price=1000000, max_price=5000000, min_size_m2=80, min_land_m2=600,
    min_rooms=3, max_rooms=5, kitchen="separate",
)
FULL_PREFERENCES = preferences(
    price_per_m2_weight=10, disposition_weight=20, preferred_dispositions=layouts("4+1", "3+kk", "atypicky"),
    size_weight=30, ideal_size_m2=120, place_weight=40,
    preferred_places=(PlaceRef("okres", 3401), PlaceRef("obec", 553786)),
    land_weight=50, ideal_land_m2=900, price_weight=60, max_good_price=4000000,
)


def _repo(tmp_path, now=None):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    return SqliteProfileRepository(conn, now=now or (lambda: BASE)), conn


class TestEnsure:
    def test_creates_the_row_once(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.ensure("praha7-byty", "Praha 7")
        repo.ensure("praha7-byty", "Praha 7")
        rows = conn.execute("SELECT id, name, paused_at, created_at FROM profiles").fetchall()
        assert len(rows) == 1
        assert rows[0]["id"] == "praha7-byty"
        assert rows[0]["paused_at"] is None
        assert rows[0]["created_at"] == BASE.isoformat()

    def test_existing_row_is_left_untouched(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.ensure("praha7-byty", "Original")
        repo.ensure("praha7-byty", "Renamed")
        row = conn.execute("SELECT name FROM profiles WHERE id = 'praha7-byty'").fetchone()
        assert row["name"] == "Original"


class TestAdd:
    def test_a_profile_reads_back_as_it_was_added(self, tmp_path):
        repo, _ = _repo(tmp_path)
        added = repo.add("Domažlicko", ("remax", "sreality"), FULL_CRITERIA, FULL_PREFERENCES)
        assert repo.get(added.id) == added

    def test_a_profile_with_every_setting_empty_reads_back_as_it_was_added(self, tmp_path):
        repo, _ = _repo(tmp_path)
        added = repo.add("Bare", (), criteria(), preferences())
        assert repo.get(added.id) == added

    def test_a_new_profile_is_not_paused(self, tmp_path):
        repo, _ = _repo(tmp_path)
        assert repo.add("P", (), criteria(), preferences()).enabled

    def test_each_profile_gets_an_id_of_its_own(self, tmp_path):
        repo, _ = _repo(tmp_path)
        first = repo.add("First", (), criteria(), preferences())
        second = repo.add("Second", (), criteria(), preferences())
        assert first.id != second.id

    def test_portals_read_back_sorted(self, tmp_path):
        """Portals have no order, so they always come back sorted."""
        repo, _ = _repo(tmp_path)
        added = repo.add("P", ("sreality", "bezrealitky", "remax"), criteria(), preferences())
        assert added.portals == ("bezrealitky", "remax", "sreality")
        assert repo.get(added.id).portals == ("bezrealitky", "remax", "sreality")

    def test_adding_leaves_the_commit_to_the_caller(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.add("P", ("sreality",), criteria(), preferences())
        conn.rollback()
        assert repo.list_profiles() == []


class TestRead:
    def test_an_unknown_id_reads_as_none(self, tmp_path):
        repo, _ = _repo(tmp_path)
        assert repo.get("nope") is None

    def test_profiles_list_oldest_first(self, tmp_path):
        """Added newest first, so the order comes from created_at alone."""
        times = iter([BASE.replace(hour=7), BASE])
        repo, _ = _repo(tmp_path, now=lambda: next(times))
        newer = repo.add("Newer", (), criteria(), preferences())
        older = repo.add("Older", (), criteria(), preferences())
        assert repo.list_profiles() == [older, newer]

    def test_each_profile_reads_back_its_own_lists(self, tmp_path):
        repo, _ = _repo(tmp_path)
        full = repo.add("Full", ("remax", "sreality"), FULL_CRITERIA, FULL_PREFERENCES)
        bare = repo.add("Bare", ("bezrealitky",), criteria(), preferences())
        assert repo.get(full.id) == full
        assert repo.get(bare.id) == bare
        assert sorted(repo.list_profiles(), key=lambda profile: profile.name) == [bare, full]

    def test_a_paused_profile_reads_as_not_enabled(self, tmp_path):
        repo, conn = _repo(tmp_path)
        added = repo.add("P", (), criteria(), preferences())
        conn.execute("UPDATE profiles SET paused_at = ? WHERE id = ?", (BASE.isoformat(), added.id))
        assert repo.get(added.id).enabled is False
