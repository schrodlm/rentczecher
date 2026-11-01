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
from rentczecher_engine.domain.location import ParsedPlace, PlaceRef
from rentczecher_engine.services.pipeline import PipelineDeps, RunCounts, run_profile
from tests.profiles import criteria, profile

BASE = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)
GAZETTEER = Gazetteer()


class FakeRunStore:
    """Every write call is counted so a test can assert none happened,
    rather than trusting the return value alone."""

    def __init__(self):
        self.seen: set[str] = set()
        self.viewed: set[str] = set()
        self.prices: dict[str, int] = {}
        self.pending: set[str] = set()
        self.persist_calls: list = []
        self.updated_keeper_ids: list[set[str]] = []
        self.prune_calls: list[str] = []

    def seen_ids(self, profile_id):
        return self.seen

    def viewed_ids(self, profile_id):
        return self.viewed

    def latest_prices(self, profile_id):
        return self.prices

    def pending_disappeared(self, profile_id, current_ids):
        return self.pending

    def prune(self, profile_id):
        self.prune_calls.append(profile_id)

    def persist_outcome(self, profile_id, outcome, located_by_id, current_ids, updated_keeper_ids):
        self.persist_calls.append((profile_id, outcome, located_by_id, current_ids))
        self.updated_keeper_ids.append(updated_keeper_ids)


def _listing(id, source, **kw):
    defaults = dict(title="t", price=20000, location_raw_text="l", url=f"https://example.com/{id}")
    defaults.update(kw)
    return Listing.build(id=f"{source}:{id}", source=source, **defaults)


def _scraper(listings=(), error=None):
    class FakeScraper:
        def __init__(self, criteria, client):
            pass

        def scrape(self):
            if error is not None:
                raise error
            return list(listings)

    return FakeScraper


def _profile(portals=("sreality",)):
    return profile(id="praha7-byty", name="Praha 7 byty", portals=portals)


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

        run_profile(_profile(), deps)

        assert len(store.persist_calls) == 1
        assert store.prune_calls == ["praha7-byty"]

    def test_a_scan_with_nothing_new_persists_once_and_prunes(self):
        store = FakeRunStore()
        store.seen = {"sreality:1"}
        store.prices = {"sreality:1": 20000}
        deps = _deps(store=store)

        run_profile(_profile(), deps)

        assert len(store.persist_calls) == 1
        assert store.prune_calls == ["praha7-byty"]


class TestDryRun:
    def test_performs_zero_store_writes(self):
        store = FakeRunStore()
        deps = _deps(store=store)

        run_profile(_profile(), deps, dry_run=True)

        assert store.persist_calls == []
        assert store.prune_calls == []


class TestScraperIsolation:
    def test_one_broken_scraper_does_not_prevent_others_listings_from_processing(self):
        scrapers = {
            "sreality": _scraper([_listing("1", "sreality")]),
            "bezrealitky": _scraper(error=ScraperBrokenError("contract changed")),
        }
        deps = _deps(scrapers=scrapers)

        result = run_profile(_profile(portals=("sreality", "bezrealitky")), deps)

        assert result.counts.new == 1
        assert result.scraper_health["sreality"].status == "ok"
        assert result.scraper_health["bezrealitky"].status == "broken"


class TestCountsAndHealth:
    def test_all_scrapers_ok_is_status_ok(self):
        deps = _deps(scrapers={"sreality": _scraper([_listing("1", "sreality")])})

        result = run_profile(_profile(), deps)

        assert result.status == "ok"
        assert result.counts == RunCounts(total=1, new=1, updated=0, price_drops=0, disappeared=0)

    def test_a_zero_results_scraper_is_status_ok(self):
        deps = _deps(scrapers={
            "sreality": _scraper([_listing("1", "sreality")]),
            "remax": _scraper([]),
        })

        result = run_profile(_profile(portals=("sreality", "remax")), deps)

        assert result.status == "ok"

    def test_a_broken_scraper_beside_a_working_one_is_status_partial(self):
        deps = _deps(scrapers={
            "sreality": _scraper([_listing("1", "sreality")]),
            "bezrealitky": _scraper(error=ScraperBrokenError("boom")),
        })

        result = run_profile(_profile(portals=("sreality", "bezrealitky")), deps)

        assert result.status == "partial"

    def test_every_scraper_broken_fails_the_run_and_persists_nothing(self):
        store = FakeRunStore()
        deps = _deps(store=store, scrapers={
            "sreality": _scraper(error=ConnectionError("offline")),
            "bezrealitky": _scraper(error=ConnectionError("offline")),
        })

        result = run_profile(_profile(portals=("sreality", "bezrealitky")), deps)

        assert result.status == "failed"
        assert set(result.scraper_health) == {"sreality", "bezrealitky"}
        assert store.persist_calls == []
        assert store.prune_calls == []

    def test_a_profile_with_no_enabled_portal_fails_the_run_and_persists_nothing(self):
        store = FakeRunStore()
        deps = _deps(store=store)

        result = run_profile(_profile(portals=()), deps)

        assert result.status == "failed"
        assert store.persist_calls == []

    def test_an_unresolvable_place_aborts_the_profile_as_failed(self, caplog):
        class UnresolvablePlaceScraper:
            def __init__(self, criteria, client):
                raise PlaceNotFoundError("obvod 78")

        deps = _deps(scrapers={"sreality": UnresolvablePlaceScraper})

        with caplog.at_level("ERROR", logger="rentczecher"):
            result = run_profile(_profile(), deps)

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

        result = run_profile(_profile(), deps)

        assert result.counts.new == 0
        assert result.counts.price_drops == 1

    def test_run_id_and_timestamps_are_populated(self):
        deps = _deps(clock=lambda: BASE)

        result = run_profile(_profile(), deps)

        assert result.run_id
        assert result.started_at == BASE
        assert result.finished_at == BASE
        assert result.profile_id == "praha7-byty"


class TestUpdatedFlats:
    def test_a_viewed_flat_whose_price_moved_is_persisted_as_updated(self):
        store = FakeRunStore()
        store.seen = {"sreality:1"}
        store.viewed = {"sreality:1"}
        store.prices = {"sreality:1": 25000}
        deps = _deps(store=store, scrapers={"sreality": _scraper([_listing("1", "sreality", price=20000)])})

        run_profile(_profile(), deps)

        assert store.updated_keeper_ids == [{"sreality:1"}]

    def test_a_dry_run_persists_no_update(self):
        store = FakeRunStore()
        store.seen = {"sreality:1"}
        store.viewed = {"sreality:1"}
        store.prices = {"sreality:1": 25000}
        deps = _deps(store=store, scrapers={"sreality": _scraper([_listing("1", "sreality", price=20000)])})

        run_profile(_profile(), deps, dry_run=True)

        assert store.updated_keeper_ids == []


class TestSearchPlaceSmallerThanTheArea:
    def test_only_listings_inside_the_place_are_kept(self):
        listings = [
            _listing("1", "sreality", parsed_place=ParsedPlace(names=("Kdyně",))),
            _listing("2", "sreality", parsed_place=ParsedPlace(names=("Poběžovice",))),
            _listing("3", "sreality", parsed_place=ParsedPlace(names=("Nová Ves",))),
        ]
        store = FakeRunStore()
        deps = _deps(store=store, scrapers={"sreality": _scraper(listings)})

        result = run_profile(profile(criteria=criteria(place=PlaceRef("obec", 553786))), deps)

        assert result.counts.total == 1
        (_, outcome, _, current_ids), = store.persist_calls
        assert [listing.id for listing in outcome.survivors] == ["sreality:1"]
        assert current_ids == {"sreality:1"}

    def test_a_listing_with_no_location_is_kept_when_the_portals_search_the_place_itself(self):
        unknown = _listing("1", "sreality", parsed_place=ParsedPlace(names=("Nová Ves",)))
        deps = _deps(scrapers={"sreality": _scraper([unknown])})

        result = run_profile(_profile(), deps)

        assert result.counts.total == 1

    def test_an_unknown_place_fails_the_run_before_any_scraper_is_built(self):
        built: list[object] = []

        class RecordingScraper:
            def __init__(self, criteria, client):
                built.append(self)

        deps = _deps(scrapers={"sreality": RecordingScraper})

        result = run_profile(profile(criteria=criteria(place=PlaceRef("obec", 999_999_999))), deps)

        assert result.status == "failed"
        assert built == []
