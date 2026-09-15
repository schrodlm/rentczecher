"""Golden test pinning the JSON-backed pipeline's stateful outcomes across runs.

Drives run_profile across a sequence of simulated scrapes and pins which
listing ids come out as NEW, which (id, old_price) pairs come out as PRICE
DROPS, and which ids come out as DISAPPEARED on each run. A storage swap
(JSON -> SQLite) must reproduce this sequence unchanged.

Run: python3 -m pytest tests/test_pipeline_golden.py -v
"""

from rentczecher.adapters import legacy_json_db as db
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.cli import main as main_module

PROFILE_ID = "golden"
PROFILE = {
    "name": "Golden profile",
    "enabled": True,
    "to": ["golden@example.com"],
    "search": {
        "offer_type": "rent",
        "estate_type": "flat",
        "place": "praha-7",
    },
    "scrapers": ["sreality"],
}

STABLE = dict(
    id="sreality:stable", source="sreality",
    title="Pronájem bytu 2+kk 50 m²", price=20000,
    location="Veletržní, Praha 7", url="https://example.com/stable",
    size_m2=50, disposition="2+kk",
)
FLAKY = dict(
    id="sreality:flaky", source="sreality",
    title="Pronájem bytu 1+kk 30 m²", price=15000,
    location="Tusarova, Praha 7", url="https://example.com/flaky",
    size_m2=30, disposition="1+kk",
)
DROPPING = dict(
    id="sreality:dropping", source="sreality",
    title="Pronájem bytu 1+1 40 m²", price=18000,
    location="Kamenická, Praha 7", url="https://example.com/dropping",
    size_m2=40, disposition="1+1",
)
DROPPING_CHEAPER = {**DROPPING, "price": 16000}


def _listings(*records):
    return [Listing.build(**r) for r in records]


def _run(monkeypatch, records):
    """Run one simulated scrape and report (new_ids, drops, disappeared_ids)."""
    listings = _listings(*records)

    class FakeScraper:
        def __init__(self, spec, client):
            pass

        def scrape(self):
            return listings

    monkeypatch.setattr(main_module, "ALL_SCRAPERS", {"sreality": FakeScraper})
    monkeypatch.setattr(main_module, "send_email", lambda *a, **k: None)

    captured = {}
    real_update_prices = db.update_prices

    def spying_update_prices(profile_id, all_listings):
        drops = real_update_prices(profile_id, all_listings)
        captured["drops"] = {(l.id, old_price) for l, old_price in drops}
        return drops

    monkeypatch.setattr(db, "update_prices", spying_update_prices)

    seen_before = set(db.get_seen(PROFILE_ID))
    real_get_disappeared = db.get_disappeared

    def spying_get_disappeared(profile_id, current_ids, **kwargs):
        disappeared = real_get_disappeared(profile_id, current_ids, **kwargs)
        captured["disappeared"] = {d["id"] for d in disappeared}
        return disappeared

    monkeypatch.setattr(db, "get_disappeared", spying_get_disappeared)

    main_module.run_profile(PROFILE_ID, PROFILE, email_cfg={}, client=None, dry_run=False)

    new_ids = {r["id"] for r in records} - seen_before
    return new_ids, captured["drops"], captured["disappeared"]


def test_first_run_reports_everything_new_and_nothing_else(tmp_path, monkeypatch):
    """Run 1: every listing is unseen, so all of them are NEW and neither
    price drops nor disappearances are reported."""
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))

    new_ids, drops, disappeared = _run(monkeypatch, [STABLE, FLAKY, DROPPING])

    assert new_ids == {"sreality:stable", "sreality:flaky", "sreality:dropping"}
    assert drops == set()
    assert disappeared == set()


def test_second_run_detects_price_drop_and_first_miss_without_disappearance(tmp_path, monkeypatch):
    """Run 2: a lowered price is reported as a drop carrying the old price,
    a missing listing counts one miss but is not yet disappeared, and
    listings present unchanged are reported neither new nor dropped."""
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    _run(monkeypatch, [STABLE, FLAKY, DROPPING])

    new_ids, drops, disappeared = _run(monkeypatch, [STABLE, DROPPING_CHEAPER])

    assert new_ids == set()
    assert drops == {("sreality:dropping", 18000)}
    assert disappeared == set()


def test_listing_missing_three_consecutive_runs_is_reported_disappeared(tmp_path, monkeypatch):
    """Runs 3-4: a listing absent from the scrape keeps accruing misses and
    is reported disappeared starting from the run where its miss count first
    reaches the threshold, and on every run after while it stays gone."""
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    _run(monkeypatch, [STABLE, FLAKY, DROPPING])
    _run(monkeypatch, [STABLE, DROPPING_CHEAPER])  # FLAKY misses once here

    _, _, disappeared_run3 = _run(monkeypatch, [STABLE, DROPPING_CHEAPER])  # miss 2
    assert disappeared_run3 == set()

    _, _, disappeared_run4 = _run(monkeypatch, [STABLE, DROPPING_CHEAPER])  # miss 3
    assert disappeared_run4 == {"sreality:flaky"}

    _, _, disappeared_run5 = _run(monkeypatch, [STABLE, DROPPING_CHEAPER])  # still gone
    assert disappeared_run5 == {"sreality:flaky"}


def test_returning_listing_resets_miss_count_and_is_not_new_again(tmp_path, monkeypatch):
    """A listing that goes missing once and then reappears has its miss
    count reset to zero and is not reported as new on its return."""
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    _run(monkeypatch, [STABLE, FLAKY, DROPPING])
    _run(monkeypatch, [STABLE, DROPPING_CHEAPER])  # FLAKY misses once

    new_ids, _, disappeared = _run(monkeypatch, [STABLE, FLAKY, DROPPING_CHEAPER])

    assert "sreality:flaky" not in new_ids
    assert disappeared == set()
    assert db.get_seen(PROFILE_ID)["sreality:flaky"]["miss_count"] == 0

    # Confirm the reset actually held: two more absences are not yet enough
    # to cross the threshold again.
    _run(monkeypatch, [STABLE, DROPPING_CHEAPER])
    _, _, disappeared_after_two_misses = _run(monkeypatch, [STABLE, DROPPING_CHEAPER])
    assert disappeared_after_two_misses == set()
