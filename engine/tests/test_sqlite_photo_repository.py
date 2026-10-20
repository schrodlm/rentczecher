"""Tests for the SQLite photo repository, against a real temp-file DB.

Run: python3 -m pytest tests/test_sqlite_photo_repository.py -v
"""

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.photos import SqlitePhotoRepository
from rentczecher_engine.domain.photo import GALLERY_LIMIT

CREATED = "2026-10-20T06:00:00+00:00"


def _repo(tmp_path):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-1', ?)", (CREATED,))
    conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                 "VALUES ('sreality:1', 'prop-1', 'sreality', 'u', ?)", (CREATED,))
    return SqlitePhotoRepository(conn), conn


def _gallery(conn, listing_id="sreality:1"):
    stmt = "SELECT position, source_url FROM listing_photos WHERE listing_id = ? ORDER BY position"
    return [tuple(row) for row in conn.execute(stmt, (listing_id,))]


class TestRecordGallery:
    def test_records_the_photos_in_the_portals_order(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", ("https://img.example/a.jpg", "https://img.example/b.jpg"))
        assert _gallery(conn) == [(0, "https://img.example/a.jpg"), (1, "https://img.example/b.jpg")]

    def test_keeps_only_the_first_photos_up_to_the_limit(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", tuple(f"https://img.example/{n}.jpg" for n in range(GALLERY_LIMIT + 5)))
        gallery = _gallery(conn)
        assert len(gallery) == GALLERY_LIMIT
        assert gallery[-1] == (GALLERY_LIMIT - 1, f"https://img.example/{GALLERY_LIMIT - 1}.jpg")

    def test_a_recorded_gallery_stays_as_it_is(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", ("https://img.example/a.jpg",))
        repo.record_gallery("sreality:1", ("https://img.example/other.jpg", "https://img.example/more.jpg"))
        assert _gallery(conn) == [(0, "https://img.example/a.jpg")]

    def test_a_listing_without_photos_records_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", ())
        assert _gallery(conn) == []
