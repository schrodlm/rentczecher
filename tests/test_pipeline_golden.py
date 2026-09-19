"""Golden test pinning the pipeline's stateful outcomes across runs.

Drives run_profile across a sequence of simulated scrapes and pins which
listing ids come out as NEW, which (id, old_price) pairs come out as PRICE
DROPS, and which ids come out as DISAPPEARED on each run.

Run: python3 -m pytest tests/test_pipeline_golden.py -v
"""

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.services.pipeline import PipelineDeps, run_profile

GAZETTEER = Gazetteer()

PROFILE_ID = "golden"
PROFILE = {
    "id": PROFILE_ID,
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


def _scraper(listings):
    class FakeScraper:
        def __init__(self, spec, client):
            pass

        def scrape(self):
            return listings

    return FakeScraper


def _run(run_store, monkeypatch, records):
    """Run one simulated scrape and report (new_ids, drops, disappeared_ids)."""
    store, _conn = run_store
    listings = _listings(*records)

    captured = {"notable": [], "disappeared": set()}

    def capture_notify(notable, spec, profile_config, disappeared):
        captured["notable"] = notable

    real_pending_disappeared = store.pending_disappeared

    def spying_pending_disappeared(profile_id, current_ids):
        disappeared = real_pending_disappeared(profile_id, current_ids)
        captured["disappeared"] = {d.id for d in disappeared}
        return disappeared

    monkeypatch.setattr(store, "pending_disappeared", spying_pending_disappeared)

    deps = PipelineDeps(
        store=store, clock=utc_now, client=None,
        scrapers={"sreality": _scraper(listings)}, gazetteer=GAZETTEER,
        notify=capture_notify,
    )

    seen_before = store.seen_ids(PROFILE_ID)
    run_profile(PROFILE, deps, dry_run=False)

    new_ids = {r["id"] for r in records} - seen_before
    drops = {(l.id, l.price_drop_from)
             for l in captured["notable"] if l.price_drop_from is not None}
    return new_ids, drops, captured["disappeared"]


def test_first_run_reports_everything_new_and_nothing_else(run_store, monkeypatch):
    """Run 1: every listing is unseen, so all of them are NEW and neither
    price drops nor disappearances are reported."""
    new_ids, drops, disappeared = _run(run_store, monkeypatch, [STABLE, FLAKY, DROPPING])

    assert new_ids == {"sreality:stable", "sreality:flaky", "sreality:dropping"}
    assert drops == set()
    assert disappeared == set()


def test_second_run_detects_price_drop_and_first_miss_without_disappearance(run_store, monkeypatch):
    """Run 2: a lowered price is reported as a drop carrying the old price,
    a missing listing counts one miss but is not yet disappeared, and
    listings present unchanged are reported neither new nor dropped."""
    _run(run_store, monkeypatch, [STABLE, FLAKY, DROPPING])

    new_ids, drops, disappeared = _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])

    assert new_ids == set()
    assert drops == {("sreality:dropping", 18000)}
    assert disappeared == set()


def test_listing_missing_three_consecutive_runs_is_reported_disappeared(run_store, monkeypatch):
    """Runs 3-4: a listing absent from the scrape keeps accruing misses and
    is reported disappeared starting from the run where its miss count first
    reaches the threshold, and on every run after while it stays gone."""
    _run(run_store, monkeypatch, [STABLE, FLAKY, DROPPING])
    _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])  # FLAKY misses once here

    _, _, disappeared_run3 = _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])  # miss 2
    assert disappeared_run3 == set()

    _, _, disappeared_run4 = _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])  # miss 3
    assert disappeared_run4 == {"sreality:flaky"}

    _, _, disappeared_run5 = _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])  # still gone
    assert disappeared_run5 == {"sreality:flaky"}


def test_returning_listing_resets_miss_count_and_is_not_new_again(run_store, monkeypatch):
    """A listing that goes missing once and then reappears has its miss
    count reset to zero and is not reported as new on its return."""
    store, conn = run_store
    _run(run_store, monkeypatch, [STABLE, FLAKY, DROPPING])
    _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])  # FLAKY misses once

    new_ids, _, disappeared = _run(run_store, monkeypatch, [STABLE, FLAKY, DROPPING_CHEAPER])

    assert "sreality:flaky" not in new_ids
    assert disappeared == set()
    row = conn.execute(
        "SELECT miss_count FROM listing_tracking WHERE listing_id = 'sreality:flaky'").fetchone()
    assert row["miss_count"] == 0

    # Confirm the reset actually held: two more absences are not yet enough
    # to cross the threshold again.
    _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])
    _, _, disappeared_after_two_misses = _run(run_store, monkeypatch, [STABLE, DROPPING_CHEAPER])
    assert disappeared_after_two_misses == set()
