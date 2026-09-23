"""In-process pub/sub feeding GET /v1/events. One process, one broker: every
subscriber gets every event published after it subscribed, nothing persists
past process lifetime."""

import json
import queue
import threading
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Literal

EventKind = Literal["run_started", "run_progress", "run_finished", "listings_arrived"]


@dataclass(frozen=True, slots=True)
class RunEvent:
    kind: EventKind
    data: dict[str, Any]

    def to_sse(self) -> str:
        return f"event: {self.kind}\ndata: {json.dumps(self.data)}\n\n"


class EventBroker:
    """Fans out published events to every currently-subscribed queue.

    A subscriber that stops reading (a dropped connection) still holds a
    queue reference until it unsubscribes. Unsubscribe is the caller's
    responsibility via the context manager subscribe() returns.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list["queue.Queue[RunEvent]"] = []

    def publish(self, event: RunEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)

    def subscribe(self) -> "_Subscription":
        subscriber: "queue.Queue[RunEvent]" = queue.Queue()
        with self._lock:
            self._subscribers.append(subscriber)
        return _Subscription(self, subscriber)

    def _unsubscribe(self, subscriber: "queue.Queue[RunEvent]") -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)


class _Subscription:
    def __init__(self, broker: EventBroker, subscriber: "queue.Queue[RunEvent]"):
        self._broker = broker
        self.queue: "queue.Queue[RunEvent]" = subscriber

    def __enter__(self) -> "queue.Queue[RunEvent]":
        return self.queue

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._broker._unsubscribe(self.queue)
