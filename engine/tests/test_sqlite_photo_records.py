"""Tests for the photo downloader's view of the database.

Run: python3 -m pytest tests/test_sqlite_photo_records.py -v
"""

from contextlib import closing
from datetime import datetime, timezone

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.photo_records import SqlitePhotoRecords
from rentczecher_engine.adapters.repositories.sqlite.photos import SqlitePhotoRepository
from rentczecher_engine.domain.photo import PendingAdvertPage

CREATED = "2026-10-20T06:00:00+00:00"
FILE_KEY = "a" * 32 + ".jpg"


READ_AT = datetime(2026, 10, 21, 6, 0, tzinfo=timezone.utc)
PAGE = PendingAdvertPage(property_id="prop-1", listing_id="sreality:1", source="sreality",
                         url="https://portal.example/1")


def _records(tmp_path):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-1', ?)", (CREATED,))
    conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                 "VALUES ('sreality:1', 'prop-1', 'sreality', 'https://portal.example/1', ?)", (CREATED,))
    SqlitePhotoRepository(conn).record_gallery("sreality:1", ("https://img.example/0.jpg",), on_advert_page=True)
    conn.commit()
    return SqlitePhotoRecords(conn, now=lambda: READ_AT)


def _committed(tmp_path, stmt):
    with closing(connection.connect(tmp_path / "t.db")) as other:
        return other.execute(stmt).fetchone()[0]


class TestSqlitePhotoRecords:
    def test_a_stored_photo_is_committed_at_once(self, tmp_path):
        records = _records(tmp_path)
        records.store_photo(records.main_photos()[0], FILE_KEY)
        assert _committed(tmp_path, "SELECT file_key FROM listing_photos") == FILE_KEY

    def test_a_failure_is_committed_at_once(self, tmp_path):
        records = _records(tmp_path)
        records.count_failure(records.main_photos()[0], give_up=False)
        assert _committed(tmp_path, "SELECT attempts FROM listing_photos") == 1

    def test_a_read_advert_gallery_is_committed_at_once(self, tmp_path):
        records = _records(tmp_path)
        records.record_advert_gallery(PAGE, ("https://img.example/big.jpg",))
        assert _committed(tmp_path, "SELECT read_at FROM advert_page_reads") == READ_AT.isoformat()
        assert _committed(tmp_path, "SELECT source_url FROM listing_photos") == "https://img.example/big.jpg"

    def test_a_failed_advert_read_is_committed_at_once(self, tmp_path):
        records = _records(tmp_path)
        records.count_advert_failure(PAGE, give_up=False)
        assert _committed(tmp_path, "SELECT attempts FROM advert_page_reads") == 1
