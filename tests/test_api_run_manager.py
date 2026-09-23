import queue
from contextlib import nullcontext
from datetime import datetime, timezone

import pytest

from rentczecher.adapters.api.events import EventBroker
from rentczecher.adapters.api.run_manager import PortalHealthEntry, RunManager
from rentczecher.domain.scrape import ScraperHealth
from rentczecher.services.pipeline import ProfileRunResult, RunCounts

BASE = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _result(new: int) -> ProfileRunResult:
    return ProfileRunResult(
        profile_id="matej", run_id="stub-run", started_at=BASE, finished_at=BASE,
        status="ok",
        scraper_health={"sreality": ScraperHealth(status="ok", error=None, listing_count=2)},
        counts=RunCounts(total=2, new=new, price_drops=0, disappeared=0),
    )


def _stub_runner(outcomes: list):
    """A services.pipeline.run_profile stand-in consuming one canned outcome
    per call: a ProfileRunResult to return or an exception to raise."""
    remaining = list(outcomes)

    def run_profile(profile_config, deps, *, dry_run=False, on_scraper_done=None):
        outcome = remaining.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if on_scraper_done is not None:
            on_scraper_done("sreality", ScraperHealth(status="ok", error=None, listing_count=2))
        return outcome

    return run_profile


def _manager(broker: EventBroker, run_profile) -> RunManager:
    return RunManager(
        lambda profile_id: nullcontext(None),
        broker,
        run_profile=run_profile,
        clock=lambda: BASE,
    )


class TestRunManager:
    def test_lifecycle_events_carry_the_returned_run_id(self):
        """A triggered run publishes started, progress, finished and
        listings_arrived, all stamped with the run id trigger returned."""
        broker = EventBroker()
        manager = _manager(broker, _stub_runner([_result(new=2)]))
        with broker.subscribe() as events:
            run_id = manager.trigger("matej", {"id": "matej"})
            collected = [events.get(timeout=2) for _ in range(4)]
        kinds = [event.kind for event in collected]
        assert kinds == ["run_started", "run_progress", "run_finished", "listings_arrived"]
        assert all(event.data["run_id"] == run_id for event in collected)

    def test_no_listings_arrived_without_new_listings(self):
        """A run finding nothing new ends at run_finished."""
        broker = EventBroker()
        manager = _manager(broker, _stub_runner([_result(new=0)]))
        with broker.subscribe() as events:
            manager.trigger("matej", {"id": "matej"})
            collected = [events.get(timeout=2) for _ in range(3)]
            assert collected[-1].kind == "run_finished"
            with pytest.raises(queue.Empty):
                events.get(timeout=0.2)

    def test_runs_execute_serially_in_trigger_order(self):
        """Two triggers close together yield two complete, non-interleaved
        event sequences in trigger order."""
        broker = EventBroker()
        manager = _manager(broker, _stub_runner([_result(new=0), _result(new=0)]))
        with broker.subscribe() as events:
            first = manager.trigger("matej", {"id": "matej"})
            second = manager.trigger("matej", {"id": "matej"})
            collected = [events.get(timeout=2) for _ in range(6)]
        assert [event.data["run_id"] for event in collected] == [first] * 3 + [second] * 3

    def test_a_failed_run_reports_failed_and_the_worker_survives(self):
        """A raising pipeline turns into run_finished with status failed, and
        the queued next run still executes."""
        broker = EventBroker()
        manager = _manager(broker, _stub_runner([RuntimeError("boom"), _result(new=0)]))
        with broker.subscribe() as events:
            manager.trigger("matej", {"id": "matej"})
            second = manager.trigger("matej", {"id": "matej"})
            failed = [events.get(timeout=2) for _ in range(2)]
            assert failed[-1].kind == "run_finished"
            assert failed[-1].data["status"] == "failed"
            assert failed[-1].data["error"] == "boom"
            rest = [events.get(timeout=2) for _ in range(3)]
        assert [event.kind for event in rest] == ["run_started", "run_progress", "run_finished"]
        assert rest[-1].data["run_id"] == second

    def test_last_health_records_the_latest_scraper_outcome(self):
        """After a run, last_health holds each portal's outcome stamped by
        the injected clock."""
        broker = EventBroker()
        manager = _manager(broker, _stub_runner([_result(new=0)]))
        with broker.subscribe() as events:
            manager.trigger("matej", {"id": "matej"})
            while events.get(timeout=2).kind != "run_finished":
                pass
        assert manager.last_health() == {
            "sreality": PortalHealthEntry(
                status="ok", error=None, listing_count=2, checked_at=BASE.isoformat()),
        }
