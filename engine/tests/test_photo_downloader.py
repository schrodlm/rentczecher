"""Tests for the photo download pass and the orphan sweep, with fakes for the
database, the files and the image servers.

Run: python3 -m pytest tests/test_photo_downloader.py -v
"""

from rentczecher_engine.domain.errors import PhotoFetchError, PhotoGoneError, PhotoRefusedError
from rentczecher_engine.domain.photo import FetchedPhoto, PendingPhoto
from rentczecher_engine.services import photos
from rentczecher_engine.services.photos import PhotoDownloader


def _photo(property_id, position=0, source="sreality"):
    listing_id = f"{source}:{property_id}"
    return PendingPhoto(property_id=property_id, listing_id=listing_id, position=position,
                        source_url=f"https://img.example/{listing_id}/{position}.jpg", source=source)


class FakeRecords:
    def __init__(self, requested=(), main=(), file_keys=(), vanished=()):
        self.requested = list(requested)
        self.main = list(main)
        self.stored_file_keys = set(file_keys)
        self.vanished = set(vanished)
        self.stored: list[tuple[str, int, str]] = []
        self.failures: list[tuple[str, int, bool]] = []

    def requested_photos(self):
        return self.requested

    def main_photos(self):
        return self.main

    def file_keys(self):
        return self.stored_file_keys

    def store_photo(self, photo, file_key):
        if photo.listing_id in self.vanished:
            return False
        self.stored.append((photo.listing_id, photo.position, file_key))
        return True

    def count_failure(self, photo, give_up):
        self.failures.append((photo.listing_id, photo.position, give_up))


class FakePhotoStore:
    def __init__(self, file_keys=()):
        self.files = set(file_keys)
        self.partials_removed = False
        self.listed_older_than_s: list[float] = []
        self._next = 0

    def put(self, content, media_type):
        self._next += 1
        file_key = f"{self._next:032x}.jpg"
        self.files.add(file_key)
        return file_key

    def delete(self, file_key):
        self.files.discard(file_key)

    def file_keys(self, older_than_s):
        self.listed_older_than_s.append(older_than_s)
        return set(self.files)

    def remove_partials(self):
        self.partials_removed = True


class FakeFetcher:
    def __init__(self, errors=None):
        self.errors = errors or {}
        self.fetched: list[str] = []

    def fetch(self, url):
        self.fetched.append(url)
        if url in self.errors:
            raise self.errors[url]
        return FetchedPhoto(content=b"jpeg", media_type="image/jpeg")


def _downloader(records, store=None, fetcher=None):
    pauses: list[float] = []
    downloader = PhotoDownloader(records, store or FakePhotoStore(), fetcher or FakeFetcher(), pause=pauses.append)
    return downloader, pauses


class TestDownloads:
    def test_stores_requested_galleries_before_main_photos(self):
        records = FakeRecords(requested=[_photo("a", 0), _photo("a", 1)],
                              main=[_photo("b")])
        downloader, _ = _downloader(records)
        downloader.run_pass()
        assert [(listing_id, position) for listing_id, position, _ in records.stored] == [
            ("sreality:a", 0), ("sreality:a", 1), ("sreality:b", 0)]

    def test_takes_main_photos_only_up_to_each_portals_budget(self, monkeypatch):
        monkeypatch.setattr(photos, "MAIN_PHOTOS_PER_PORTAL", 2)
        records = FakeRecords(main=[_photo("a"), _photo("b"), _photo("c"), _photo("d", source="remax")])
        downloader, _ = _downloader(records)
        downloader.run_pass()
        assert [listing_id for listing_id, _, _ in records.stored] == ["sreality:a", "sreality:b", "remax:d"]

    def test_pauses_before_each_download_shorter_for_a_requested_gallery(self):
        records = FakeRecords(requested=[_photo("a", 0), _photo("a", 1)],
                              main=[_photo("b")])
        downloader, pauses = _downloader(records)
        downloader.run_pass()
        assert pauses == [photos.REQUESTED_PHOTO_PAUSE_S, photos.REQUESTED_PHOTO_PAUSE_S, photos.MAIN_PHOTO_PAUSE_S]

    def test_asks_a_refusing_portal_nothing_more_in_the_pass(self):
        refused = _photo("a")
        records = FakeRecords(main=[refused, _photo("b"), _photo("c", source="remax")])
        fetcher = FakeFetcher(errors={refused.source_url: PhotoRefusedError("403")})
        downloader, _ = _downloader(records, fetcher=fetcher)
        downloader.run_pass()
        assert fetcher.fetched == [refused.source_url, _photo("c", source="remax").source_url]
        assert records.failures == []

    def test_gives_up_a_photo_that_is_gone(self):
        gone = _photo("a")
        records = FakeRecords(main=[gone])
        downloader, _ = _downloader(records, fetcher=FakeFetcher(errors={gone.source_url: PhotoGoneError("404")}))
        downloader.run_pass()
        assert records.failures == [("sreality:a", 0, True)]

    def test_counts_any_other_failure_as_an_attempt(self):
        failing = _photo("a")
        records = FakeRecords(main=[failing])
        downloader, _ = _downloader(records, fetcher=FakeFetcher(errors={failing.source_url: PhotoFetchError("500")}))
        downloader.run_pass()
        assert records.failures == [("sreality:a", 0, False)]

    def test_deletes_the_file_of_a_photo_gone_while_downloading(self):
        store = FakePhotoStore()
        records = FakeRecords(main=[_photo("a")], vanished={"sreality:a"})
        downloader, _ = _downloader(records, store=store)
        downloader.run_pass()
        assert store.files == set()

    def test_reports_each_property_once_its_photos_are_done(self):
        records = FakeRecords(requested=[_photo("a", 0), _photo("a", 1)],
                              main=[_photo("b")])
        downloader, _ = _downloader(records)
        done: list[str] = []
        downloader.run_pass(on_property_done=done.append)
        assert done == ["a", "b"]

    def test_a_waiting_request_cuts_the_main_photos_short(self):
        records = FakeRecords(requested=[_photo("a", 0), _photo("a", 1)], main=[_photo("b"), _photo("c")])
        downloader, _ = _downloader(records)
        downloader.run_pass(should_yield=lambda: len(records.stored) >= 1)
        assert [listing_id for listing_id, _, _ in records.stored] == ["sreality:a", "sreality:a"]


class TestSweep:
    def test_deletes_files_no_photo_refers_to(self):
        kept = "a" * 32 + ".jpg"
        orphan = "b" * 32 + ".jpg"
        store = FakePhotoStore(file_keys={kept, orphan})
        downloader, _ = _downloader(FakeRecords(file_keys={kept}), store=store)
        downloader.run_pass()
        assert store.files == {kept}
        assert store.partials_removed

    def test_spares_files_too_new_to_be_recorded(self):
        store = FakePhotoStore()
        downloader, _ = _downloader(FakeRecords(), store=store)
        downloader.run_pass()
        assert store.listed_older_than_s == [photos.SWEEP_GRACE_S]
