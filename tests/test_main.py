"""Tests for main.py orchestration.

Run: python3 -m pytest tests/test_main.py -v
"""

import os

import db
import main as main_module
from scrapers.base import Listing


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
    return Listing(**defaults)


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
