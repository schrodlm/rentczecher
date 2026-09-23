import queue
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from rentczecher.adapters.api.events import EventBroker

router = APIRouter()

# How often the generator wakes up with nothing to send, so a dropped
# connection is noticed instead of blocking the worker forever.
_POLL_SECONDS = 1.0


def iter_sse_events(broker: EventBroker, *, poll_seconds: float = _POLL_SECONDS) -> Iterator[str]:
    """The event stream's body as SSE-formatted text, one item per
    published event. Runs until the caller stops iterating (a dropped
    connection raises GeneratorExit here, which the subscription's __exit__
    turns into an unsubscribe)."""
    with broker.subscribe() as subscriber:
        while True:
            try:
                event = subscriber.get(timeout=poll_seconds)
            except queue.Empty:
                continue
            yield event.to_sse()


@router.get("/v1/events")
def stream_events(request: Request) -> StreamingResponse:
    broker = request.app.state.event_broker
    return StreamingResponse(iter_sse_events(broker), media_type="text/event-stream")
