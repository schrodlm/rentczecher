"""Tests for main.py orchestration.

Run: python3 -m pytest tests/test_main.py -v
"""

import os
import sys

import pytest

from rentczecher.adapters import legacy_json_db as db
from rentczecher.cli import main as main_module
from rentczecher.adapters.scrapers.base import Listing, ScraperBrokenError


class TestOrphanedRepoDataWarning:
    """When runs store data away from an existing repo-local installation,
    the stranded seen-listing history is called out loudly."""

    def test_warns_when_repo_data_exists_but_is_unused(self, tmp_path, monkeypatch, caplog):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-praha7.json").write_text("{}")
        monkeypatch.setattr(main_module.paths, "repo_root", lambda: repo)
        monkeypatch.setattr(db, "DATA_DIR", str(tmp_path / "xdg-data"))
        monkeypatch.delenv("RENTCZECHER_DATA_DIR", raising=False)
        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module._warn_if_repo_data_orphaned()
        assert any("seen-*.json" in r.message for r in caplog.records)

    def test_silent_when_repo_data_is_the_active_data_dir(self, tmp_path, monkeypatch, caplog):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-praha7.json").write_text("{}")
        monkeypatch.setattr(main_module.paths, "repo_root", lambda: repo)
        monkeypatch.setattr(db, "DATA_DIR", str(repo / "data"))
        monkeypatch.delenv("RENTCZECHER_DATA_DIR", raising=False)
        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module._warn_if_repo_data_orphaned()
        assert not caplog.records

    def test_silent_under_explicit_data_override(self, tmp_path, monkeypatch, caplog):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-praha7.json").write_text("{}")
        monkeypatch.setattr(main_module.paths, "repo_root", lambda: repo)
        monkeypatch.setattr(db, "DATA_DIR", str(tmp_path / "explicit"))
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
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
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


class TestBrokenScraperHandling:
    """A scraper raising ScraperBrokenError is reported as a distinct ERROR
    and does not abort the profile: the remaining scrapers' listings still
    flow through the pipeline."""

    def test_broken_scraper_is_reported_and_run_continues(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
        healthy_listing = _make_listing(id="sreality:good", title="Good listing")

        class WorkingScraper:
            name = "sreality"

            def __init__(self, spec, client):
                pass

            def scrape(self):
                return [healthy_listing]

        class BrokenScraper:
            name = "bezrealitky"

            def __init__(self, spec, client):
                pass

            def scrape(self):
                raise ScraperBrokenError("bezrealitky: __NEXT_DATA__ payload missing from search page")

        monkeypatch.setattr(main_module, "ALL_SCRAPERS",
                            {"sreality": WorkingScraper, "bezrealitky": BrokenScraper})
        profile = {
            "name": "Broken-portal test",
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
            "scrapers": ["sreality", "bezrealitky"],
        }
        with caplog.at_level("INFO", logger="rentczecher"):
            main_module.run_profile("broken-test", profile, email_cfg={}, client=None, dry_run=True)

        contract_errors = [r for r in caplog.records if "portal changed its contract" in r.getMessage()]
        assert len(contract_errors) == 1
        assert contract_errors[0].levelname == "ERROR"
        assert "__NEXT_DATA__" in contract_errors[0].getMessage()
        assert not any(r.exc_info for r in caplog.records), "broken portal must not dump a stack trace"
        assert any("Total: 1 listings, 1 new" in r.getMessage() for r in caplog.records)


class TestUnresolvablePlace:
    """A profile whose place cannot resolve fails once with a clean error
    naming the place, not once per scraper with stack traces."""

    def test_profile_fails_once_without_tracebacks(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
        from rentczecher.adapters.scrapers import ALL_SCRAPERS
        monkeypatch.setattr(main_module, "ALL_SCRAPERS", ALL_SCRAPERS)
        profile = {
            "name": "Bad place",
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "atlantis"},
            "scrapers": ["sreality", "bezrealitky", "remax"],
        }
        with caplog.at_level("ERROR", logger="rentczecher"):
            main_module.run_profile("bad-place", profile, email_cfg={}, client=None, dry_run=True)
        errors = [r for r in caplog.records if "atlantis" in r.getMessage()]
        assert len(errors) == 1
        assert not any(r.exc_info for r in caplog.records)


class TestEmptyScraperList:
    """A profile with an empty scrapers list is valid config and skips
    cleanly at runtime."""

    def test_empty_list_validates_and_skips(self, caplog):
        from rentczecher.adapters.config.schema import ProfileConfig
        ProfileConfig.model_validate({
            "name": "P", "to": ["a@example.com"],
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
            "scrapers": [],
        })
        profile = {"name": "Empty", "search": {"offer_type": "rent", "estate_type": "flat",
                                               "place": "praha-7"}, "scrapers": []}
        with caplog.at_level("WARNING", logger="rentczecher"):
            main_module.run_profile("empty", profile, email_cfg={}, client=None, dry_run=True)
        assert any("no enabled scrapers" in r.getMessage() for r in caplog.records)


class TestDryRunIsReadOnly:
    """--dry-run writes no state; miss counters advance only on real runs."""

    def _run_dry(self, profile_id, monkeypatch):
        fake_new = _make_listing(id="sreality:new", title="New listing")

        class FakeScraper:
            name = "sreality"

            def __init__(self, spec, client):
                pass

            def scrape(self):
                return [fake_new]

        monkeypatch.setattr(main_module, "ALL_SCRAPERS", {"sreality": FakeScraper})
        profile = {
            "name": "Dry-run test",
            "search": {"offer_type": "rent", "estate_type": "flat", "place": "praha-7"},
            "scrapers": ["sreality"],
        }
        main_module.run_profile(profile_id, profile, email_cfg={}, client=None, dry_run=True)

    def test_dry_run_leaves_seen_file_byte_identical(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
        profile_id = "dryrun-test"

        # Seed a listing the fake scrape will NOT return, so the miss-count
        # write would have to happen if dry-run were not read-only.
        db.mark_seen(profile_id, [_make_listing(id="sreality:old", title="Old")])

        path = db._db_path(profile_id)
        with open(path, "rb") as f:
            before = f.read()
        mtime_before = os.path.getmtime(path)

        self._run_dry(profile_id, monkeypatch)
        self._run_dry(profile_id, monkeypatch)

        with open(path, "rb") as f:
            after = f.read()
        assert after == before
        assert os.path.getmtime(path) == mtime_before
