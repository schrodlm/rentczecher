"""Tests for services/pipeline.run_profile's orchestration.

Fakes satisfy the RunStore protocol in-memory (no mocking framework) and
record every write call, so commit-every-scan and dry-run's zero-writes
invariant are pinned by call counts, not by inspecting a real database.

Run: python3 -m pytest tests/test_run_profile.py -v
"""

from datetime import datetime, timezone

from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.domain.errors import PlaceNotFoundError, ScraperBrokenError
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.services.pipeline import PipelineDeps, RunCounts, run_profile

BASE = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)
GAZETTEER = Gazetteer()


class FakeRunStore:
    """Every write call is counted so a test can assert none happened,
    rather than trusting the return value alone."""

    def __init__(self):
        self.seen: set[str] = set()
        self.prices: dict[str, int] = {}
        self.pending: set[str] = set()
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
    defaults = dict(title="t", price=20000, location_raw_text="l", url=f"https://example.com/{id}")
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
        id="praha7-byty", name="Praha 7 byty",
        search={"offer_type": "rent", "estate_type": "flat", "place": PlaceRef("obvod", 78)},
        scrapers=list(scrapers),
    )
    config.update(overrides)
    return config


def _deps(store=None, scrapers=None, clock=None):
    return PipelineDeps(
        store=store if store is not None else FakeRunStore(),
        clock=clock if clock is not None else (lambda: BASE),
        client=None,
        scrapers=scrapers if scrapers is not None else {"sreality": _scraper([_listing("1", "sreality")])},
        gazetteer=GAZETTEER,
    )


class TestCommit:
    def test_a_scan_with_new_listings_persists_once_and_prunes(self):
        store = FakeRunStore()
        deps = _deps(store=store)

        run_profile(_profile_config(), deps)

        assert len(store.persist_calls) == 1
        assert store.prune_calls == ["praha7-byty"]

    def test_a_scan_with_nothing_new_persists_once_and_prunes(self):
        store = FakeRunStore()
        store.seen = {"sreality:1"}
        store.prices = {"sreality:1": 20000}
        deps = _deps(store=store)

        run_profile(_profile_config(), deps)

        assert len(store.persist_calls) == 1
        assert store.prune_calls == ["praha7-byty"]


class TestDryRun:
    def test_performs_zero_store_writes(self):
        store = FakeRunStore()
        deps = _deps(store=store)

        run_profile(_profile_config(), deps, dry_run=True)

        assert store.persist_calls == []
        assert store.prune_calls == []


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

    def test_an_unresolvable_place_aborts_the_profile_as_failed(self, caplog):
        class UnresolvablePlaceScraper:
            def __init__(self, spec, client):
                raise PlaceNotFoundError("obvod 78")

        deps = _deps(scrapers={"sreality": UnresolvablePlaceScraper})

        with caplog.at_level("ERROR", logger="rentczecher"):
            result = run_profile(_profile_config(), deps)

        assert result.status == "failed"
        assert result.counts.total == 0
        assert not any(r.exc_info for r in caplog.records), "an unresolvable place must not dump a stack trace"
        assert "obvod 78" in (result.error or "")
        errors = [r for r in caplog.records if "obvod 78" in r.getMessage()]
        assert len(errors) == 1

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
