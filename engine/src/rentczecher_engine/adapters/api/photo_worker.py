"""Runs photo passes on a background thread of its own, so a download never
holds up a scan or a request."""

import logging
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager

from rentczecher_engine.adapters.api.events import EventBroker, GalleryChangedEvent, RunEvent
from rentczecher_engine.services.photos import PhotoDownloader

log = logging.getLogger("rentczecher.api")


class PhotoWorker:
    """Passes asked for while one runs collapse into a single pass after it.
    A pass asked for while main photos download cuts them short, so a
    gallery someone waits on comes first."""

    def __init__(self, open_downloader: Callable[[], AbstractContextManager[PhotoDownloader]],
                 broker: EventBroker):
        self._open_downloader = open_downloader
        self._broker = broker
        self._wanted = threading.Event()
        self._thread = threading.Thread(target=self._drain, name="rentczecher-photo-worker", daemon=True)
        self._thread.start()

    def request_pass(self) -> None:
        self._wanted.set()

    def _drain(self) -> None:
        while True:
            self._wanted.wait()
            self._wanted.clear()
            self._run_pass()

    def _run_pass(self) -> None:
        try:
            with self._open_downloader() as downloader:
                downloader.run_pass(on_property_done=self._announce, should_yield=self._wanted.is_set)
        except Exception:
            log.exception("photo pass failed")

    def _announce(self, property_id: str) -> None:
        self._broker.publish(RunEvent(
            kind="gallery_changed", data=GalleryChangedEvent(property_id=property_id).model_dump()))
