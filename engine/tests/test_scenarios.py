"""Tests for the scenario loader and the shipped scenarios: each replays into
the inbox its file describes."""

from datetime import datetime, timedelta, timezone

import pytest

from rentczecher_engine.adapters.repositories.sqlite import connection
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore
from tests.scenarios import Scenario, offset_from_now

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def replayed(name, tmp_path):
    """The store over a scenario replayed into tmp_path, plus its raw connection."""
    Scenario.load(name).replay_into(tmp_path, NOW)
    conn = connection.connect(tmp_path / "data" / "rentczecher.db")
    return SqliteRunStore(conn), conn


@pytest.mark.parametrize("name", Scenario.names())
def test_every_scenario_replays(name, tmp_path):
    """Each shipped scenario file loads and replays without error."""
    Scenario.load(name).replay_into(tmp_path, NOW)
    assert (tmp_path / "config.yaml").is_file()
    assert (tmp_path / "data" / "rentczecher.db").is_file()


def test_empty_leaves_an_empty_inbox(tmp_path):
    """A scan that found nothing leaves the profile with no cards."""
    store, _ = replayed("empty", tmp_path)
    assert store.inbox_listings("empty") == []


def test_fresh_scrape_shows_new_and_viewed_listings(tmp_path):
    """The viewed list marks exactly those listings viewed, the rest stay new."""
    store, _ = replayed("fresh-scrape", tmp_path)
    cards = store.inbox_listings("fresh-scrape")
    assert len(cards) == 6
    assert {card.id for card in cards if card.viewed_at is not None} == {"sreality:1002", "remax:3001"}


def test_price_drops_carries_the_earlier_price(tmp_path):
    """A listing seen again at a lower price reports the price it dropped from."""
    store, _ = replayed("price-drops", tmp_path)
    by_id = {card.id: card for card in store.inbox_listings("price-drops")}
    assert by_id["sreality:1101"].price == 22500
    assert by_id["sreality:1101"].price_drop_from == 25000
    assert by_id["bezrealitky:2101"].price_drop_from is None


def test_price_drops_dates_listings_by_their_first_scan(tmp_path):
    """Relative scan times land on the replay's clock: first seen three days
    before now."""
    store, _ = replayed("price-drops", tmp_path)
    card = next(card for card in store.inbox_listings("price-drops") if card.id == "sreality:1101")
    assert datetime.fromisoformat(card.first_seen_at) == NOW - timedelta(days=3)


def test_disappeared_misses_the_listing_three_scans_in_a_row(tmp_path):
    """A listing absent from the last three scans carries three misses, its
    neighbour none."""
    _, conn = replayed("disappeared", tmp_path)
    stmt = "SELECT listing_id, miss_count FROM listing_tracking WHERE profile_id = ?"
    misses = {row["listing_id"]: row["miss_count"] for row in conn.execute(stmt, ("disappeared",))}
    assert misses == {"sreality:1201": 3, "sreality:1202": 0}


def test_cross_portal_folds_the_same_flat_into_one_property(tmp_path):
    """The two postings of one flat point at each other as siblings, the
    unrelated flat has none."""
    store, _ = replayed("cross-portal", tmp_path)
    siblings = {card.id: {s.source for s in card.sibling_sources} for card in store.inbox_listings("cross-portal")}
    assert siblings == {"sreality:1301": {"bezrealitky"}, "bezrealitky:2301": {"sreality"}, "remax:3301": set()}


def test_replaying_onto_an_existing_database_is_refused(tmp_path):
    """A second replay into the same folder fails rather than stacking a
    second story onto the first."""
    Scenario.load("empty").replay_into(tmp_path, NOW)
    with pytest.raises(ValueError, match="already holds a database"):
        Scenario.load("empty").replay_into(tmp_path, NOW)


def test_an_unknown_scenario_names_the_known_ones():
    """Asking for a missing scenario lists the ones that exist."""
    with pytest.raises(ValueError, match="known: .*fresh-scrape"):
        Scenario.load("no-such-scenario")


def test_an_unknown_top_level_key_is_rejected():
    """A misspelled top-level key fails instead of being ignored."""
    with pytest.raises(ValueError, match="unknown keys \\['scan'\\]"):
        Scenario.from_text("typo", "profile: {}\nscan: []\n")


def test_an_unknown_listing_field_fails_loudly(tmp_path):
    """A listing field the engine does not know stops the replay rather than
    being dropped."""
    scenario = Scenario.from_text("typo", """
profile:
  name: Typo
  search: {offer_type: rent, estate_type: flat, place: obvod Praha 7}
scans:
  - at: -1h
    listings:
      - {id: "sreality:1", price: 20000, sise_m2: 50}
""")
    with pytest.raises(TypeError, match="sise_m2"):
        scenario.replay_into(tmp_path, NOW)


@pytest.mark.parametrize("text, expected", [
    ("now", timedelta(0)),
    ("-3d", -timedelta(days=3)),
    ("-2h", -timedelta(hours=2)),
    ("-30m", -timedelta(minutes=30)),
])
def test_offsets_count_back_from_now(text, expected):
    """Days, hours and minutes count back from the replay's now."""
    assert offset_from_now(text) == expected


@pytest.mark.parametrize("text", ["3d", "-3w", "yesterday", "-d"])
def test_a_malformed_offset_is_rejected(text):
    """Anything but now or a negative day, hour or minute offset fails."""
    with pytest.raises(ValueError, match="expected 'now' or an offset"):
        offset_from_now(text)
