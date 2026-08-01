"""Tests for main.py orchestration.

Run: python3 -m pytest tests/test_main.py -v
"""

import os

from rentczecher.adapters import legacy_json_db as db
from rentczecher.cli import main as main_module
from rentczecher.adapters.scrapers.base import Listing


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


class TestDryRunIsReadOnly:
    """--dry-run writes no state; miss counters advance only on real runs."""

    def _run_dry(self, profile_id, monkeypatch):
        fake_new = _make_listing(id="sreality:new", title="New listing")

        class FakeScraper:
            name = "sreality"

            def __init__(self, profile):
                pass

            def scrape(self):
                return [fake_new]

        monkeypatch.setattr(main_module, "ALL_SCRAPERS", {"sreality": FakeScraper})
        profile = {
            "name": "Dry-run test",
            "search": {},
            "scrapers": {"sreality": {"enabled": True}},
        }
        main_module.run_profile(profile_id, profile, email_cfg={}, dry_run=True)

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
