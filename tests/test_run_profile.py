"""Tests for services/pipeline.run_profile's orchestration.

Fakes satisfy the RunStore protocol in-memory (no mocking framework) and
record every write call, so notify-then-commit and dry-run's zero-writes
invariant are pinned by call counts, not by inspecting a real database.

Run: python3 -m pytest tests/test_run_profile.py -v
"""

from datetime import datetime, timezone

import pytest

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.domain.errors import PlaceNotFoundError, ScraperBrokenError
from rentczecher.domain.listing import Listing
from rentczecher.services.pipeline import PipelineDeps, RunCounts, run_profile

BASE = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)
GAZETTEER = Gazetteer()


class FakeRunStore:
    """Every write call is counted so a test can assert none happened,
    rather than trusting the return value alone."""

    def __init__(self):
        self.seen: set[str] = set()
        self.prices: dict[str, int] = {}
        self.pending: list = []
        self.persist_calls: list = []
        self.prune_calls: list[str] = []

    def seen_ids(self, profile_id):
        return self.seen

    def latest_prices(self, profile_id):
        return self.prices

    def pending_disappeared(self, profile_id, current_ids):
        return self.pending

    def prune(self, profile_id):
        self.prune_calls.append(profile_id)

    def persist_outcome(self, profile_id, profile_name, outcome, located_by_id, current_ids):
        self.persist_calls.append((profile_id, profile_name, outcome, located_by_id, current_ids))


def _listing(id, source, **kw):
    defaults = dict(title="t", price=20000, location="l", url=f"https://example.com/{id}")
    defaults.update(kw)
    return Listing.build(id=f"{source}:{id}", source=source, **defaults)


def _scraper(listings=(), error=None):
    class FakeScraper:
        def __init__(self, spec, client):
            pass

        def scrape(self):
            if error is not None:
                raise error
            return list(listings)

    return FakeScraper


def _profile_config(scrapers=("sreality",), **overrides):
    config = dict(
        id="praha7-byty", name="Praha 7 byty", to=["owner@example.com"],
        search={"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
        scrapers=list(scrapers),
    )
    config.update(overrides)
    return config


def _deps(store=None, notify=None, scrapers=None, clock=None, enrich_tram=None):
    return PipelineDeps(
        store=store if store is not None else FakeRunStore(),
        clock=clock if clock is not None else (lambda: BASE),
        client=None,
        scrapers=scrapers if scrapers is not None else {"sreality": _scraper([_listing("1", "sreality")])},
        gazetteer=GAZETTEER,
        enrich_tram=enrich_tram if enrich_tram is not None else (lambda listing: listing),
        notify=notify if notify is not None else (lambda *a, **k: None),
    )


class TestNotifyThenCommit:
    def test_a_raising_notify_persists_nothing_including_miss_counters(self):
        store = FakeRunStore()

        def raising_notify(*args, **kwargs):
            raise RuntimeError("smtp exploded")

        deps = _deps(store=store, notify=raising_notify)

        with pytest.raises(RuntimeError):
            run_profile(_profile_config(), deps)

        assert store.persist_calls == []
        assert store.prune_calls == []

    def test_a_notify_returning_false_persists_nothing(self):
        store = FakeRunStore()
        deps = _deps(store=store, notify=lambda *a, **k: False)

        run_profile(_profile_config(), deps)

        assert store.persist_calls == []
        assert store.prune_calls == []

    def test_a_successful_notify_persists_once(self):
        store = FakeRunStore()
        deps = _deps(store=store, notify=lambda *a, **k: True)

        run_profile(_profile_config(), deps)

        assert len(store.persist_calls) == 1
        assert store.prune_calls == ["praha7-byty"]

    def test_no_recipients_persists_but_does_not_prune(self):
        store = FakeRunStore()
        deps = _deps(store=store, notify=lambda *a, **k: True)

        run_profile(_profile_config(to=[]), deps)

        assert len(store.persist_calls) == 1
        assert store.prune_calls == []

    def test_nothing_notable_persists_without_calling_notify(self):
        calls = []

        def spying_notify(*args, **kwargs):
            calls.append(args)
            return True

        store = FakeRunStore()
        store.seen = {"sreality:1"}
        store.prices = {"sreality:1": 20000}
        deps = _deps(store=store, notify=spying_notify)

        run_profile(_profile_config(), deps)

        assert calls == []
        assert len(store.persist_calls) == 1
        assert store.prune_calls == []


class TestDryRun:
    def test_performs_zero_store_writes(self):
        store = FakeRunStore()
        deps = _deps(store=store, notify=lambda *a, **k: True)

        run_profile(_profile_config(), deps, dry_run=True)

        assert store.persist_calls == []
        assert store.prune_calls == []

    def test_does_not_call_notify(self):
        calls = []
        store = FakeRunStore()
        deps = _deps(store=store, notify=lambda *a, **k: calls.append(1))

        run_profile(_profile_config(), deps, dry_run=True)

        assert calls == []


class TestScraperIsolation:
    def test_one_broken_scraper_does_not_prevent_others_listings_from_processing(self):
        scrapers = {
            "sreality": _scraper([_listing("1", "sreality")]),
            "bezrealitky": _scraper(error=ScraperBrokenError("contract changed")),
        }
        deps = _deps(scrapers=scrapers)

        result = run_profile(_profile_config(scrapers=("sreality", "bezrealitky")), deps)

        assert result.counts.new == 1
        assert result.scraper_health["sreality"].status == "ok"
        assert result.scraper_health["bezrealitky"].status == "broken"


class TestCountsAndHealth:
    def test_all_scrapers_ok_is_status_ok(self):
        deps = _deps(scrapers={"sreality": _scraper([_listing("1", "sreality")])})

        result = run_profile(_profile_config(), deps)

        assert result.status == "ok"
        assert result.counts == RunCounts(total=1, new=1, price_drops=0, disappeared=0)

    def test_a_zero_results_scraper_is_status_ok(self):
        deps = _deps(scrapers={
            "sreality": _scraper([_listing("1", "sreality")]),
            "remax": _scraper([]),
        })

        result = run_profile(_profile_config(scrapers=("sreality", "remax")), deps)

        assert result.status == "ok"

    def test_a_broken_scraper_is_status_partial(self):
        deps = _deps(scrapers={"sreality": _scraper(error=ScraperBrokenError("boom"))})

        result = run_profile(_profile_config(), deps)

        assert result.status == "partial"

    def test_an_unresolvable_place_aborts_the_profile_as_failed(self):
        class UnresolvablePlaceScraper:
            def __init__(self, spec, client):
                raise PlaceNotFoundError(spec.place, ())

        deps = _deps(scrapers={"sreality": UnresolvablePlaceScraper})

        result = run_profile(_profile_config(), deps)

        assert result.status == "failed"
        assert result.counts.total == 0

    def test_a_seen_listing_reported_at_a_lower_price_counts_as_a_price_drop(self):
        store = FakeRunStore()
        store.seen = {"sreality:1"}
        store.prices = {"sreality:1": 25000}
        deps = _deps(store=store, scrapers={
            "sreality": _scraper([_listing("1", "sreality", price=20000)])
        })

        result = run_profile(_profile_config(), deps)

        assert result.counts.new == 0
        assert result.counts.price_drops == 1

    def test_run_id_and_timestamps_are_populated(self):
        deps = _deps(clock=lambda: BASE)

        result = run_profile(_profile_config(), deps)

        assert result.run_id
        assert result.started_at == BASE
        assert result.finished_at == BASE
        assert result.profile_id == "praha7-byty"


def test_tram_enrichment_runs_only_when_the_profile_enables_it():
    calls = []

    def enrich(listing):
        calls.append(listing.id)
        return listing

    deps = _deps(enrich_tram=enrich, scrapers={
        "sreality": _scraper([_listing("1", "sreality")])
    })

    run_profile(_profile_config(tram_enrichment=True), deps)

    assert calls == ["sreality:1"]
