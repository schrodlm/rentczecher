"""Tests for the file photo store.

Run: python3 -m pytest tests/test_photo_store.py -v
"""

import os
import time

import pytest

from rentczecher_engine.adapters.photos.store import FilePhotoStore, media_type_of


class TestPut:
    def test_stores_the_photo_under_a_key_carrying_its_type(self, tmp_path):
        store = FilePhotoStore(tmp_path / "photos")
        file_key = store.put(b"jpeg bytes", "image/jpeg")
        assert file_key.endswith(".jpg")
        assert store.path(file_key).read_bytes() == b"jpeg bytes"
        assert media_type_of(file_key) == "image/jpeg"

    def test_gives_every_photo_its_own_key(self, tmp_path):
        store = FilePhotoStore(tmp_path)
        assert store.put(b"a", "image/png") != store.put(b"a", "image/png")

    def test_leaves_no_partial_file_behind(self, tmp_path):
        store = FilePhotoStore(tmp_path)
        store.put(b"a", "image/webp")
        assert [path.suffix for path in tmp_path.iterdir()] == [".webp"]


def _written_ago(store, file_key, seconds):
    written_at = time.time() - seconds
    os.utime(store.path(file_key), (written_at, written_at))


class TestFileKeys:
    def test_lists_the_stored_keys(self, tmp_path):
        store = FilePhotoStore(tmp_path)
        file_key = store.put(b"a", "image/jpeg")
        (tmp_path / "notes.txt").write_text("not a photo")
        assert store.file_keys(older_than_s=0) == {file_key}

    def test_leaves_out_files_written_more_recently(self, tmp_path):
        store = FilePhotoStore(tmp_path)
        old = store.put(b"a", "image/jpeg")
        _written_ago(store, old, 120)
        store.put(b"b", "image/jpeg")
        assert store.file_keys(older_than_s=60) == {old}

    def test_an_empty_store_has_no_keys(self, tmp_path):
        assert FilePhotoStore(tmp_path / "never-created").file_keys(older_than_s=0) == set()


class TestDelete:
    def test_deletes_the_photo(self, tmp_path):
        store = FilePhotoStore(tmp_path)
        file_key = store.put(b"a", "image/jpeg")
        store.delete(file_key)
        assert store.file_keys(older_than_s=0) == set()

    def test_deleting_a_missing_photo_is_a_no_op(self, tmp_path):
        FilePhotoStore(tmp_path).delete("0" * 32 + ".jpg")


class TestRemovePartials:
    def test_removes_half_written_files_and_keeps_photos(self, tmp_path):
        store = FilePhotoStore(tmp_path)
        file_key = store.put(b"a", "image/jpeg")
        (tmp_path / ("1" * 32 + ".jpg.part")).write_bytes(b"half")
        store.remove_partials()
        assert sorted(path.name for path in tmp_path.iterdir()) == [file_key]


class TestPath:
    @pytest.mark.parametrize("file_key", ["../outside.jpg", "abc.jpg", "0" * 32 + ".exe", "0" * 32])
    def test_refuses_anything_but_a_photo_key(self, tmp_path, file_key):
        with pytest.raises(ValueError):
            FilePhotoStore(tmp_path).path(file_key)
