"""Tests for main.py orchestration.

Run: python3 -m pytest tests/test_main.py -v
"""

import io
import sys
import time
from contextlib import closing

import pytest

from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.cli import main as main_module
from rentczecher_engine.services.pipeline import PipelineDeps, run_profile
from tests.profiles import profile, stored_profile


class TestEmptyPortalList:
    """A profile that scans no portals is skipped with a warning."""

    def test_warns_and_skips_the_profile(self, tmp_path, monkeypatch, caplog):
        db_path = tmp_path / "t.db"
        with closing(connection.connect(db_path)) as conn:
            migrate.apply_pending(conn)
            stored_profile(conn, name="Empty", portals=())
        monkeypatch.setattr(main_module.paths, "db_path", lambda: db_path)
        monkeypatch.setattr(main_module, "PID_PATH", str(tmp_path / "watchdog.pid"))

        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module.run(dry_run=True)

        assert any("scans no portals" in r.getMessage() for r in caplog.records)


class TestDbMigrate:
    def test_migrate_builds_the_database(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(main_module.paths, "db_path",
                            lambda: tmp_path / "rentczecher.db")
        assert main_module.migrate_db() == 0
        db = tmp_path / "rentczecher.db"
        assert db.exists()
        import sqlite3
        conn = sqlite3.connect(db)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 12
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "properties" in tables and "listings" in tables

    def test_migrate_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main_module.paths, "db_path",
                            lambda: tmp_path / "rentczecher.db")
        assert main_module.migrate_db() == 0
        assert main_module.migrate_db() == 0

    def test_bare_db_command_errors_instead_of_scraping(self, monkeypatch):
        # A bare `rentczecher db` must not fall through to a real scrape run.
        monkeypatch.setattr(sys, "argv", ["rentczecher", "db"])
        ran = []
        monkeypatch.setattr(main_module, "run", lambda **kw: ran.append(kw))
        with pytest.raises(SystemExit):
            main_module.main()
        assert ran == []


class TestServe:
    def test_missing_token_fails_fast_without_starting_the_server(self, monkeypatch, caplog):
        monkeypatch.delenv("RENTCZECHER_API_TOKEN", raising=False)
        started = []
        monkeypatch.setattr(main_module.uvicorn, "run", lambda *a, **kw: started.append(True))
        with caplog.at_level("ERROR", logger="rentczecher"):
            exit_code = main_module.serve(8734, allowed_origins=[])
        assert exit_code == 1
        assert started == []
        assert any("RENTCZECHER_API_TOKEN" in r.message for r in caplog.records)


    def test_announces_the_bound_port_on_stdout(self, monkeypatch, capsys, tmp_path):
        """With port 0, serve binds a free port and prints it as PORT=<n>
        before serving on that same socket."""
        monkeypatch.setenv("RENTCZECHER_API_TOKEN", "test-token")
        monkeypatch.setattr(main_module.paths, "db_path", lambda: tmp_path / "t.db")
        served = []
        monkeypatch.setattr(main_module.uvicorn.Server, "run",
                            lambda self, sockets=None: served.extend(sockets))

        assert main_module.serve(0, allowed_origins=[]) == 0

        port = served[0].getsockname()[1]
        served[0].close()
        assert port > 0
        assert capsys.readouterr().out.strip().splitlines()[-1] == f"PORT={port}"


    def test_shutdown_callback_stops_the_server(self, monkeypatch, tmp_path):
        """The callback serve hands to the app sets the running server's
        exit flag, the same flag uvicorn's own Ctrl-C handler sets."""
        monkeypatch.setenv("RENTCZECHER_API_TOKEN", "test-token")
        monkeypatch.setattr(main_module.paths, "db_path", lambda: tmp_path / "t.db")
        created = {}
        real_create_app = main_module.create_app

        def recording_create_app(*args, **kwargs):
            created["request_shutdown"] = kwargs["request_shutdown"]
            return real_create_app(*args, **kwargs)

        servers = []

        def fake_run(self, sockets=None):
            servers.append(self)
            for sock in sockets:
                sock.close()

        monkeypatch.setattr(main_module, "create_app", recording_create_app)
        monkeypatch.setattr(main_module.uvicorn.Server, "run", fake_run)

        main_module.serve(0, allowed_origins=[])
        created["request_shutdown"]()

        assert servers[0].should_exit is True


    def test_exit_with_parent_stops_the_server_at_end_of_stdin(self, monkeypatch, tmp_path):
        """With exit_with_parent, stdin reaching end of input makes the
        running server exit, as when the spawner dies."""
        monkeypatch.setenv("RENTCZECHER_API_TOKEN", "test-token")
        monkeypatch.setattr(main_module.paths, "db_path", lambda: tmp_path / "t.db")
        monkeypatch.setattr(main_module.sys, "stdin", io.TextIOWrapper(io.BytesIO(b"")))
        exited = []

        def fake_run(self, sockets=None):
            for sock in sockets:
                sock.close()
            deadline = time.monotonic() + 2
            while not self.should_exit and time.monotonic() < deadline:
                time.sleep(0.01)
            exited.append(self.should_exit)

        monkeypatch.setattr(main_module.uvicorn.Server, "run", fake_run)

        main_module.serve(0, allowed_origins=[], exit_with_parent=True)

        assert exited == [True]


class TestPidLock:
    """A second invocation against the same resolved data dir must refuse
    to run while the first one is alive."""

    def test_second_acquire_fails_while_holder_is_alive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main_module, "PID_PATH", str(tmp_path / "data" / "watchdog.pid"))
        assert main_module._acquire_pidlock() is True
        # The lock file now holds this test process's own (alive) PID.
        assert main_module._acquire_pidlock() is False
        main_module._release_pidlock()
        assert main_module._acquire_pidlock() is True
        main_module._release_pidlock()


def _make_listing(**kwargs):
    defaults = dict(
        id="sreality:1",
        source="sreality",
        title="Prodej domu 120 m2",
        price=3_000_000,
        location_raw_text="Nekvasovy, okres Plzeň-jih",
        url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def _scraper(*listings):
    class FakeScraper:
        def __init__(self, criteria, client):
            pass

        def scrape(self):
            return list(listings)

    return FakeScraper


def _deps(store):
    return PipelineDeps(
        store=store,
        clock=utc_now,
        client=None,
        scrapers={"sreality": _scraper(_make_listing(id="sreality:new", title="New listing"))},
        gazetteer=Gazetteer(),
    )


class TestDryRunIsReadOnly:
    """A dry run writes no state. Miss counters advance only on real runs."""

    def test_dry_run_leaves_the_database_untouched(self, run_store):
        store, conn = run_store
        profile_id = "dryrun-test"

        # Seed a listing the fake scrape will NOT return, so the miss-count
        # write would have to happen if dry run were not read only.
        conn.execute("INSERT INTO profiles (id, name, created_at) "
                     "VALUES (?, 'Dry-run test', 't')", (profile_id,))
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-old', 't')")
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES ('sreality:old', 'prop-old', 'sreality', 'u', 't')")
        conn.execute("INSERT INTO listing_tracking (profile_id, listing_id, "
                     "first_seen_at, last_seen_at, miss_count) "
                     "VALUES (?, 'sreality:old', 't', 't', 0)", (profile_id,))
        conn.commit()

        def state():
            tracking = conn.execute(
                "SELECT profile_id, listing_id, miss_count FROM listing_tracking "
                "ORDER BY listing_id").fetchall()
            listings = conn.execute("SELECT count(*) FROM listings").fetchone()[0]
            observations = conn.execute("SELECT count(*) FROM price_observations").fetchone()[0]
            return [tuple(r) for r in tracking], listings, observations

        before = state()

        deps = _deps(store)
        run_profile(profile(id=profile_id, name="Dry-run test"), deps, dry_run=True)
        run_profile(profile(id=profile_id, name="Dry-run test"), deps, dry_run=True)

        assert state() == before
        assert store.seen_ids(profile_id) == {"sreality:old"}


class TestCommittedScanPrunes:
    """Every committed scan forgets the profile's stale tracking rows."""

    def test_stale_tracking_is_pruned(self, run_store):
        store, conn = run_store
        profile_id = "prune-test"

        conn.execute("INSERT INTO profiles (id, name, created_at) "
                     "VALUES (?, 'Prune test', 't')", (profile_id,))
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-stale', 't')")
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES ('sreality:stale', 'prop-stale', 'sreality', 'u', 't')")
        conn.execute("INSERT INTO listing_tracking (profile_id, listing_id, "
                     "first_seen_at, last_seen_at, miss_count) "
                     "VALUES (?, 'sreality:stale', '2000-01-01T00:00:00+00:00', "
                     "'2000-01-01T00:00:00+00:00', 0)", (profile_id,))
        conn.commit()

        run_profile(profile(id=profile_id, name="Prune test"), _deps(store))

        remaining = conn.execute(
            "SELECT listing_id FROM listing_tracking WHERE profile_id = ? ORDER BY listing_id", (profile_id,)
        ).fetchall()
        assert [r["listing_id"] for r in remaining] == ["sreality:new"]
