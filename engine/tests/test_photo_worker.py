"""Tests for the photo worker's passes.

Run: python3 -m pytest tests/test_photo_worker.py -v
"""

import threading
from contextlib import contextmanager

from rentczecher_engine.adapters.api.events import EventBroker
from rentczecher_engine.adapters.api.photo_worker import PhotoWorker


class FakeDownloader:
    def __init__(self, done_properties=(), fail=False):
        self.done_properties = list(done_properties)
        self.fail = fail
        self.during_first_pass = None
        self.passes = threading.Semaphore(0)
        self.yielded: list[bool] = []

    def run_pass(self, on_property_done, should_yield):
        if not self.yielded and self.during_first_pass is not None:
            self.during_first_pass()
        self.yielded.append(should_yield())
        for property_id in self.done_properties:
            on_property_done(property_id)
        self.passes.release()
        if self.fail:
            raise RuntimeError("image server exploded")


def _worker(downloader, broker=None):
    @contextmanager
    def open_downloader():
        yield downloader

    return PhotoWorker(open_downloader, broker or EventBroker())


class TestPhotoWorker:
    def test_runs_no_pass_until_asked(self):
        downloader = FakeDownloader()
        _worker(downloader)
        assert not downloader.passes.acquire(timeout=0.2)

    def test_a_pass_asked_for_during_one_makes_it_yield_and_follows(self):
        downloader = FakeDownloader()
        worker = _worker(downloader)
        downloader.during_first_pass = worker.request_pass
        worker.request_pass()
        assert downloader.passes.acquire(timeout=2)
        assert downloader.passes.acquire(timeout=2)
        assert downloader.yielded == [True, False]

    def test_announces_each_property_whose_photos_are_done(self):
        broker = EventBroker()
        downloader = FakeDownloader(done_properties=["prop-1"])
        with broker.subscribe() as events:
            _worker(downloader, broker).request_pass()
            event = events.get(timeout=2)
        assert (event.kind, event.data) == ("gallery_changed", {"property_id": "prop-1"})

    def test_keeps_running_after_a_failed_pass(self):
        downloader = FakeDownloader(fail=True)
        worker = _worker(downloader)
        worker.request_pass()
        assert downloader.passes.acquire(timeout=2)
        worker.request_pass()
        assert downloader.passes.acquire(timeout=2)
