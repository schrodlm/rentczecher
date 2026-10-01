import queue
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from rentczecher.adapters.api.events import EventBroker

router = APIRouter()

# A generator only learns that its stream ended (a dropped connection, a
# server shutdown) when it yields. On a quiet stream it would never yield and
# its worker thread would block until the next event, so it yields an SSE
# comment every poll interval. EventSource ignores comment lines.
_POLL_SECONDS = 1.0
_KEEPALIVE = ": keepalive\n\n"


def iter_sse_events(broker: EventBroker, *, poll_seconds: float = _POLL_SECONDS) -> Iterator[str]:
    """The event stream's body as SSE-formatted text: one item per published
    event, and a keepalive comment whenever poll_seconds pass without one.
    Runs until the caller stops iterating (a dropped connection raises
    GeneratorExit here, which the subscription's __exit__ turns into an
    unsubscribe)."""
    with broker.subscribe() as subscriber:
        while True:
            try:
                event = subscriber.get(timeout=poll_seconds)
            except queue.Empty:
                yield _KEEPALIVE
                continue
            yield event.to_sse()


@router.get("/v1/events")
def stream_events(request: Request) -> StreamingResponse:
    broker = request.app.state.event_broker
    return StreamingResponse(iter_sse_events(broker), media_type="text/event-stream")
