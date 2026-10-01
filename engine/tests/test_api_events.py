import queue
from typing import get_args

import pytest

from rentczecher.adapters.api.events import (
    EVENT_PAYLOADS,
    EventBroker,
    EventKind,
    RunCountsModel,
    RunEvent,
    RunFinishedEvent,
    RunProgressEvent,
)


class TestEventBroker:
    def test_publish_reaches_every_subscriber(self):
        """A published event lands in every currently-subscribed queue."""
        broker = EventBroker()
        with broker.subscribe() as first, broker.subscribe() as second:
            event = RunEvent(kind="run_started", data={"profile": "matej"})
            broker.publish(event)
            assert first.get_nowait() == event
            assert second.get_nowait() == event

    def test_subscriber_sees_only_events_after_subscribing(self):
        """Events published before a queue subscribed never reach it."""
        broker = EventBroker()
        broker.publish(RunEvent(kind="run_started", data={}))
        with broker.subscribe() as subscriber:
            with pytest.raises(queue.Empty):
                subscriber.get_nowait()

    def test_context_exit_unsubscribes(self):
        """Leaving the subscription context stops delivery to that queue."""
        broker = EventBroker()
        with broker.subscribe() as subscriber:
            pass
        broker.publish(RunEvent(kind="run_finished", data={}))
        with pytest.raises(queue.Empty):
            subscriber.get_nowait()


class TestRunEvent:
    def test_to_sse_wire_format(self):
        """to_sse frames the event as an SSE message: event line, data line, blank line."""
        event = RunEvent(kind="run_progress", data={"scraper": "sreality"})
        assert event.to_sse() == 'event: run_progress\ndata: {"scraper": "sreality"}\n\n'


class TestEventPayloads:
    def test_every_event_kind_has_a_payload_model(self):
        """EVENT_PAYLOADS pairs each event kind with exactly one model."""
        assert set(EVENT_PAYLOADS) == set(get_args(EventKind))

    def test_run_progress_wire_shape(self):
        """A progress payload carries the portal, its status, and its count."""
        payload = RunProgressEvent(
            run_id="r1", profile_id="matej", scraper="sreality", status="ok", listing_count=143)
        assert payload.model_dump() == {
            "run_id": "r1",
            "profile_id": "matej",
            "scraper": "sreality",
            "status": "ok",
            "listing_count": 143,
        }

    def test_run_finished_carries_counts_on_success_and_error_on_failure(self):
        """The finished payload is one shape with two halves: counts filled
        on success, error filled on failure, the other explicitly null."""
        ok = RunFinishedEvent(
            run_id="r1", profile_id="matej", status="ok",
            counts=RunCountsModel(total=2, new=1, price_drops=0, disappeared=0))
        assert ok.model_dump() == {
            "run_id": "r1",
            "profile_id": "matej",
            "status": "ok",
            "counts": {"total": 2, "new": 1, "price_drops": 0, "disappeared": 0},
            "error": None,
        }
        failed = RunFinishedEvent(run_id="r1", profile_id="matej", status="failed", error="boom")
        assert failed.model_dump() == {
            "run_id": "r1",
            "profile_id": "matej",
            "status": "failed",
            "counts": None,
            "error": "boom",
        }
