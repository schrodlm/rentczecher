"""Tests for the SQLite photo repository, against a real temp-file DB.

Run: python3 -m pytest tests/test_sqlite_photo_repository.py -v
"""

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.photos import SqlitePhotoRepository
from rentczecher_engine.domain.photo import GALLERY_LIMIT, MAX_ATTEMPTS

CREATED = "2026-10-20T06:00:00+00:00"
FILE_KEY = "a" * 32 + ".jpg"


def _repo(tmp_path):
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('p', 'P', ?)", (CREATED,))
    _add_listing(conn, "prop-1", "sreality:1")
    return SqlitePhotoRepository(conn), conn


def _add_listing(conn, property_id, listing_id, first_seen_at=CREATED):
    conn.execute("INSERT OR IGNORE INTO properties (id, created_at) VALUES (?, ?)", (property_id, CREATED))
    conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) VALUES (?, ?, ?, ?, ?)",
                 (listing_id, property_id, listing_id.split(":")[0], f"https://portal.example/{listing_id}", CREATED))
    conn.execute("INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, last_seen_at) "
                 "VALUES ('p', ?, ?, ?)", (listing_id, first_seen_at, first_seen_at))
    conn.execute("INSERT OR IGNORE INTO property_tracking (profile_id, property_id) VALUES ('p', ?)", (property_id,))


def _urls(count, listing_id="sreality:1"):
    return tuple(f"https://img.example/{listing_id}/{n}.jpg" for n in range(count))


def _wanted(photos):
    return [(photo.listing_id, photo.position) for photo in photos]


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

    def test_marks_a_gallery_on_the_advert_page_as_unread_once(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(1), on_advert_page=True)
        conn.execute("UPDATE advert_page_reads SET read_at = ?", (CREATED,))
        repo.record_gallery("sreality:1", _urls(1), on_advert_page=True)
        stmt = "SELECT listing_id, read_at FROM advert_page_reads"
        assert [tuple(row) for row in conn.execute(stmt)] == [("sreality:1", CREATED)]

    def test_a_listing_without_photos_records_none(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", ())
        assert _gallery(conn) == []


class TestMainPhotos:
    def test_wants_each_flats_main_photo_only(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(3))
        assert _wanted(repo.main_photos()) == [("sreality:1", 0)]

    def test_takes_the_main_photo_of_the_listing_with_the_most_photos(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-1", "bezrealitky:1")
        repo.record_gallery("sreality:1", _urls(2))
        repo.record_gallery("bezrealitky:1", _urls(5, "bezrealitky:1"))
        assert _wanted(repo.main_photos()) == [("bezrealitky:1", 0)]

    def test_wants_the_flat_seen_last_first(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-2", "sreality:2", first_seen_at="2026-10-21T06:00:00+00:00")
        repo.record_gallery("sreality:1", _urls(1))
        repo.record_gallery("sreality:2", _urls(1, "sreality:2"))
        assert _wanted(repo.main_photos()) == [("sreality:2", 0), ("sreality:1", 0)]

    def test_leaves_out_a_requested_flat(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(3))
        repo.request_gallery("p", "prop-1", CREATED)
        assert repo.main_photos() == []

    def test_leaves_out_a_stored_or_given_up_photo(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-2", "sreality:2")
        repo.record_gallery("sreality:1", _urls(1))
        repo.record_gallery("sreality:2", _urls(1, "sreality:2"))
        repo.store_photo("sreality:1", 0, _urls(1)[0], FILE_KEY)
        repo.count_failure("sreality:2", 0, give_up=True)
        assert repo.main_photos() == []


class TestRequestGallery:
    def test_records_a_request_for_a_tracked_flat(self, tmp_path):
        repo, conn = _repo(tmp_path)
        assert repo.request_gallery("p", "prop-1", CREATED)
        assert [row["property_id"] for row in conn.execute("SELECT property_id FROM gallery_requests")] == ["prop-1"]

    def test_refuses_a_flat_the_profile_does_not_track(self, tmp_path):
        repo, conn = _repo(tmp_path)
        assert not repo.request_gallery("p", "prop-unknown", CREATED)
        assert conn.execute("SELECT count(*) FROM gallery_requests").fetchone()[0] == 0


class TestRequestedPhotos:
    def test_wants_the_whole_gallery_of_a_requested_flat(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(3))
        repo.request_gallery("p", "prop-1", CREATED)
        assert _wanted(repo.requested_photos()) == [("sreality:1", 0), ("sreality:1", 1), ("sreality:1", 2)]

    def test_wants_the_latest_request_first(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-2", "sreality:2")
        repo.record_gallery("sreality:1", _urls(1))
        repo.record_gallery("sreality:2", _urls(1, "sreality:2"))
        repo.request_gallery("p", "prop-1", "2026-10-20T07:00:00+00:00")
        repo.request_gallery("p", "prop-2", "2026-10-20T08:00:00+00:00")
        assert _wanted(repo.requested_photos()) == [("sreality:2", 0), ("sreality:1", 0)]

    def test_a_photo_failing_too_often_is_no_longer_wanted(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(1))
        repo.request_gallery("p", "prop-1", CREATED)
        for _ in range(MAX_ATTEMPTS):
            repo.count_failure("sreality:1", 0, give_up=False)
        assert repo.requested_photos() == []


def _unread_advert(repo, listing_id="sreality:1", photo_count=1):
    repo.record_gallery(listing_id, _urls(photo_count, listing_id), on_advert_page=True)


class TestRequestedAdvertPages:
    def test_wants_the_advert_page_of_a_requested_gallery(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        repo.request_gallery("p", "prop-1", CREATED)
        (page,) = repo.requested_advert_pages()
        assert (page.property_id, page.listing_id, page.source, page.url) == (
            "prop-1", "sreality:1", "sreality", "https://portal.example/sreality:1")

    def test_leaves_out_an_unrequested_flat(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        assert repo.requested_advert_pages() == []

    def test_leaves_out_a_page_already_read_or_given_up(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-2", "sreality:2")
        _unread_advert(repo)
        _unread_advert(repo, "sreality:2")
        repo.request_gallery("p", "prop-1", CREATED)
        repo.request_gallery("p", "prop-2", CREATED)
        repo.record_advert_gallery("sreality:1", _urls(3), CREATED)
        repo.count_advert_failure("sreality:2", give_up=True)
        assert repo.requested_advert_pages() == []

    def test_leaves_out_a_flat_whose_gallery_comes_from_another_listing(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-1", "sreality:2")
        _unread_advert(repo)
        repo.record_gallery("sreality:2", _urls(5, "sreality:2"))
        repo.request_gallery("p", "prop-1", CREATED)
        assert repo.requested_advert_pages() == []

    def test_a_page_failing_too_often_is_no_longer_wanted(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        repo.request_gallery("p", "prop-1", CREATED)
        for _ in range(MAX_ATTEMPTS):
            repo.count_advert_failure("sreality:1", give_up=False)
        assert repo.requested_advert_pages() == []


class TestRecordAdvertGallery:
    def test_replaces_the_gallery_with_the_pages(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        page_urls = ("https://img.example/big/0.jpg", "https://img.example/big/1.jpg")
        repo.record_advert_gallery("sreality:1", page_urls, CREATED)
        assert _gallery(conn) == [(0, page_urls[0]), (1, page_urls[1])]

    def test_a_photo_listed_again_keeps_its_file(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        repo.store_photo("sreality:1", 0, _urls(1)[0], FILE_KEY)
        repo.record_advert_gallery("sreality:1", ("https://img.example/other.jpg", _urls(1)[0]), CREATED)
        assert repo.file_keys() == {FILE_KEY}
        stmt = "SELECT file_key FROM listing_photos WHERE position = 1"
        assert conn.execute(stmt).fetchone()[0] == FILE_KEY

    def test_keeps_only_the_first_photos_up_to_the_limit(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        repo.record_advert_gallery("sreality:1", _urls(GALLERY_LIMIT + 5), CREATED)
        assert len(_gallery(conn)) == GALLERY_LIMIT

    def test_a_page_listing_no_photos_leaves_the_searchs_in_place(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        repo.record_advert_gallery("sreality:1", (), CREATED)
        assert _gallery(conn) == [(0, _urls(1)[0])]
        assert conn.execute("SELECT read_at FROM advert_page_reads").fetchone()[0] == CREATED

    def test_a_listing_deleted_meanwhile_is_left_alone(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        conn.execute("DELETE FROM listings")
        repo.record_advert_gallery("sreality:1", _urls(2), CREATED)
        assert conn.execute("SELECT count(*) FROM listing_photos").fetchone()[0] == 0

    def test_marks_the_page_read(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo)
        repo.record_advert_gallery("sreality:1", _urls(2), CREATED)
        assert conn.execute("SELECT read_at FROM advert_page_reads").fetchone()[0] == CREATED


class TestStorePhoto:
    def test_records_the_stored_file(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(1))
        assert repo.store_photo("sreality:1", 0, _urls(1)[0], FILE_KEY)
        assert repo.file_keys() == {FILE_KEY}

    def test_says_when_the_photo_is_gone(self, tmp_path):
        repo, conn = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(1))
        conn.execute("DELETE FROM listings")
        assert not repo.store_photo("sreality:1", 0, _urls(1)[0], FILE_KEY)


class TestMainPhotoKeys:
    def test_maps_each_tracked_flat_to_its_stored_main_photo(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-2", "sreality:2")
        repo.record_gallery("sreality:1", _urls(2))
        repo.record_gallery("sreality:2", _urls(1, "sreality:2"))
        repo.store_photo("sreality:1", 0, _urls(2)[0], FILE_KEY)
        assert repo.main_photo_keys("p") == {"prop-1": FILE_KEY}

    def test_leaves_out_other_profiles_flats(self, tmp_path):
        repo, conn = _repo(tmp_path)
        conn.execute("INSERT INTO profiles (id, name, created_at) VALUES ('q', 'Q', ?)", (CREATED,))
        repo.record_gallery("sreality:1", _urls(1))
        repo.store_photo("sreality:1", 0, _urls(1)[0], FILE_KEY)
        assert repo.main_photo_keys("q") == {}


class TestGallery:
    def test_none_for_a_flat_the_profile_does_not_track(self, tmp_path):
        repo, _ = _repo(tmp_path)
        assert repo.gallery("p", "prop-unknown") is None

    def test_a_flat_without_photos_has_none(self, tmp_path):
        repo, _ = _repo(tmp_path)
        gallery = repo.gallery("p", "prop-1")
        assert (gallery.photo_count, gallery.status) == (0, "none")

    def test_downloading_while_its_main_photo_is_not_stored(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(3))
        gallery = repo.gallery("p", "prop-1")
        assert (gallery.photo_count, gallery.file_keys, gallery.status) == (3, (), "downloading")

    def test_stored_once_its_main_photo_is_for_a_flat_never_requested(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(3))
        repo.store_photo("sreality:1", 0, _urls(3)[0], FILE_KEY)
        gallery = repo.gallery("p", "prop-1")
        assert (gallery.file_keys, gallery.status) == ((FILE_KEY,), "stored")

    def test_downloading_while_a_requested_gallery_is_incomplete(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(3))
        repo.store_photo("sreality:1", 0, _urls(3)[0], FILE_KEY)
        repo.request_gallery("p", "prop-1", CREATED)
        assert repo.gallery("p", "prop-1").status == "downloading"

    def test_failed_when_every_photo_is_given_up(self, tmp_path):
        repo, _ = _repo(tmp_path)
        repo.record_gallery("sreality:1", _urls(1))
        repo.count_failure("sreality:1", 0, give_up=True)
        assert repo.gallery("p", "prop-1").status == "failed"

    def test_downloading_while_a_requested_gallerys_advert_page_is_unread(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo, photo_count=0)
        repo.request_gallery("p", "prop-1", CREATED)
        assert repo.gallery("p", "prop-1").status == "downloading"

    def test_downloading_while_an_advert_page_is_unread_before_any_request(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo, photo_count=0)
        assert repo.gallery("p", "prop-1").status == "downloading"

    def test_settles_once_the_advert_page_is_read(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _unread_advert(repo, photo_count=0)
        repo.record_advert_gallery("sreality:1", (), CREATED)
        assert repo.gallery("p", "prop-1").status == "none"

    def test_shows_the_listing_with_the_most_photos(self, tmp_path):
        repo, conn = _repo(tmp_path)
        _add_listing(conn, "prop-1", "bezrealitky:1")
        repo.record_gallery("sreality:1", _urls(2))
        repo.record_gallery("bezrealitky:1", _urls(5, "bezrealitky:1"))
        gallery = repo.gallery("p", "prop-1")
        assert (gallery.source, gallery.url, gallery.photo_count) == (
            "bezrealitky", "https://portal.example/bezrealitky:1", 5)
