"""Tests for main.py orchestration.

Run: python3 -m pytest tests/test_main.py -v
"""

import sys

import pytest

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.notifiers.smtp import NoRecipientsNotifier, build_smtp_notifier
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.cli import main as main_module
from rentczecher.services.pipeline import PipelineDeps, run_profile


class TestOrphanedRepoDataWarning:
    """When runs store data away from an existing repo-local installation,
    the stranded seen-listing history is called out loudly."""

    def test_warns_when_repo_data_exists_but_is_unused(self, tmp_path, monkeypatch, caplog):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-praha7.json").write_text("{}")
        monkeypatch.setattr(main_module.paths, "repo_root", lambda: repo)
        monkeypatch.setattr(main_module.paths, "data_dir", lambda: tmp_path / "xdg-data")
        monkeypatch.delenv("RENTCZECHER_DATA_DIR", raising=False)
        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module._warn_if_repo_data_orphaned()
        assert any("seen-*.json" in r.message for r in caplog.records)

    def test_silent_when_repo_data_is_the_active_data_dir(self, tmp_path, monkeypatch, caplog):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-praha7.json").write_text("{}")
        monkeypatch.setattr(main_module.paths, "repo_root", lambda: repo)
        monkeypatch.setattr(main_module.paths, "data_dir", lambda: repo / "data")
        monkeypatch.delenv("RENTCZECHER_DATA_DIR", raising=False)
        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module._warn_if_repo_data_orphaned()
        assert not caplog.records

    def test_silent_under_explicit_data_override(self, tmp_path, monkeypatch, caplog):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-praha7.json").write_text("{}")
        monkeypatch.setattr(main_module.paths, "repo_root", lambda: repo)
        monkeypatch.setattr(main_module.paths, "data_dir", lambda: tmp_path / "explicit")
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "explicit"))
        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module._warn_if_repo_data_orphaned()
        assert not caplog.records


class TestValidateConfig:


    def test_validate_reports_profile_and_scraper_counts(self, tmp_path, capsys):
        import yaml
        config = {
            "email": {"smtp_host": "h", "smtp_user": "u",
                      "smtp_password": "p", "from": "u@example.com"},
            "profiles": {"p": {
                "name": "P", "to": ["a@example.com"],
                "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
                "scrapers": ["sreality", "bezrealitky", "remax"],
            }},
        }
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(config))
        assert main_module.validate_config(path) == 0
        assert capsys.readouterr().out == "OK - 1 profile(s), 3 scraper(s) enabled\n"

    def test_validate_reports_error_for_a_legacy_config(self, tmp_path, capsys):
        import yaml
        config = {
            "email": {"smtp_host": "h", "smtp_user": "u",
                      "smtp_password": "p", "from": "u@example.com"},
            "profiles": {"p": {
                "name": "P", "to": ["a@example.com"],
                "search": {"offer_type": "rent", "estate_type": "flat"},
                "scrapers": {"sreality": {"enabled": True, "locality_district_id": 5007}},
            }},
        }
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(config))
        assert main_module.validate_config(path) == 1
        err = capsys.readouterr().err
        assert "place" in err
        assert "scrapers" in err


class TestEmptyScraperList:
    """A profile whose scrapers list resolves to zero enabled scrapers is
    valid config, but must not run silently."""

    def test_warns_and_skips_the_profile(self, tmp_path, monkeypatch, caplog):
        import yaml

        config = {
            "email": {"smtp_host": "h", "smtp_user": "u",
                      "smtp_password": "p", "from": "u@example.com"},
            "profiles": {"empty": {
                "name": "Empty", "to": ["a@example.com"],
                "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
                "scrapers": [],
            }},
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.safe_dump(config))
        monkeypatch.setattr(main_module, "CONFIG_PATH", str(config_path))
        monkeypatch.setattr(main_module.paths, "db_path", lambda: tmp_path / "t.db")
        monkeypatch.setattr(main_module, "PID_PATH", str(tmp_path / "watchdog.pid"))

        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module.run(dry_run=True)

        assert any("no enabled scrapers" in r.getMessage() for r in caplog.records)


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
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
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
        location="Nekvasovy, okres Plzeň-jih",
        url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def _scraper(*listings):
    class FakeScraper:
        def __init__(self, spec, client):
            pass

        def scrape(self):
            return list(listings)

    return FakeScraper


class _SilentNotifier:
    def send(self, notification) -> bool:
        return True


class TestDryRunIsReadOnly:
    """A dry run writes no state. Miss counters advance only on real runs."""

    def _deps(self, store):
        return PipelineDeps(
            store=store,
            clock=utc_now,
            client=None,
            scrapers={"sreality": _scraper(_make_listing(id="sreality:new", title="New listing"))},
            gazetteer=Gazetteer(),
            notifier=_SilentNotifier(),
        )

    def _profile(self, profile_id):
        return {
            "id": profile_id, "name": "Dry-run test",
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
            "scrapers": ["sreality"],
        }

    def test_dry_run_leaves_the_database_untouched(self, run_store):
        store, conn = run_store
        profile_id = "dryrun-test"

        # Seed a listing the fake scrape will NOT return, so the miss-count
        # write would have to happen if dry run were not read only.
        conn.execute("INSERT INTO profiles (id, name, active, created_at) "
                     "VALUES (?, 'Dry-run test', 1, 't')", (profile_id,))
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

        deps = self._deps(store)
        run_profile(self._profile(profile_id), deps, dry_run=True)
        run_profile(self._profile(profile_id), deps, dry_run=True)

        assert state() == before
        assert store.seen_ids(profile_id) == {"sreality:old"}


class TestNotifierSkipsEmailWithoutRecipients:
    """A profile with notable listings but no 'to' recipients still
    persists its outcome, but skips pruning stale tracking - only a real
    send stands in for the owner having seen the run's results. The missing-
    recipients error logs only when a notification is actually attempted."""

    def test_outcome_persists_but_stale_tracking_is_kept(self, run_store):
        store, conn = run_store
        profile_id = "no-recipients"

        conn.execute("INSERT INTO profiles (id, name, active, created_at) "
                     "VALUES (?, 'No recipients', 1, 't')", (profile_id,))
        conn.execute("INSERT INTO properties (id, created_at) VALUES ('prop-stale', 't')")
        conn.execute("INSERT INTO listings (id, property_id, source, url, scraped_at) "
                     "VALUES ('sreality:stale', 'prop-stale', 'sreality', 'u', 't')")
        conn.execute("INSERT INTO listing_tracking (profile_id, listing_id, "
                     "first_seen_at, last_seen_at, miss_count) "
                     "VALUES (?, 'sreality:stale', '2000-01-01T00:00:00+00:00', "
                     "'2000-01-01T00:00:00+00:00', 0)", (profile_id,))
        conn.commit()

        notifier = build_smtp_notifier(
            email_cfg={}, profile_id=profile_id, recipients=[]) or NoRecipientsNotifier(profile_id)
        deps = PipelineDeps(
            store=store,
            clock=utc_now,
            client=None,
            scrapers={"sreality": _scraper(_make_listing(id="sreality:new", title="New listing"))},
            gazetteer=Gazetteer(),
            notifier=notifier,
        )
        profile = {
            "id": profile_id, "name": "No recipients", "to": [],
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
            "scrapers": ["sreality"],
        }

        run_profile(profile, deps)

        remaining = conn.execute(
            "SELECT listing_id FROM listing_tracking WHERE profile_id = ? ORDER BY listing_id", (profile_id,)
        ).fetchall()
        assert [r["listing_id"] for r in remaining] == ["sreality:new", "sreality:stale"]

    def test_missing_recipients_error_only_logs_when_something_is_notable(self, run_store, caplog):
        store, conn = run_store
        profile_id = "no-recipients"

        conn.execute("INSERT INTO profiles (id, name, active, created_at) "
                     "VALUES (?, 'No recipients', 1, 't')", (profile_id,))
        conn.commit()

        notifier = build_smtp_notifier(
            email_cfg={}, profile_id=profile_id, recipients=[]) or NoRecipientsNotifier(profile_id)
        profile = {
            "id": profile_id, "name": "No recipients", "to": [],
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
            "scrapers": ["sreality"],
        }

        with caplog.at_level("ERROR", logger="rentczecher"):
            deps = PipelineDeps(
                store=store, clock=utc_now, client=None,
                scrapers={"sreality": _scraper()}, gazetteer=Gazetteer(), notifier=notifier,
            )
            run_profile(profile, deps)
        assert not caplog.records

        caplog.clear()
        with caplog.at_level("ERROR", logger="rentczecher"):
            deps = PipelineDeps(
                store=store, clock=utc_now, client=None,
                scrapers={"sreality": _scraper(_make_listing(id="sreality:new", title="New listing"))},
                gazetteer=Gazetteer(), notifier=notifier,
            )
            run_profile(profile, deps)
        assert any("has no 'to' recipients configured" in r.getMessage() for r in caplog.records)
