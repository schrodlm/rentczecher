import queue

import pytest

from rentczecher.adapters.api.events import EventBroker, RunEvent


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
