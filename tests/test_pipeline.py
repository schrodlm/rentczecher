"""Tests for the pipeline's structural contracts and result types.

Run: python3 -m pytest tests/test_pipeline.py -v
"""

import dataclasses
from datetime import datetime, timezone

import pytest

from rentczecher.services.pipeline import (
    ProfileRunResult,
    RunCounts,
    RunStore,
    ScraperHealth,
)


def test_sqlite_run_store_structurally_satisfies_run_store(run_store):
    store, _conn = run_store
    assert isinstance(store, RunStore)


class TestResultTypesConstructAndAreFrozen:
    def test_scraper_health(self):
        health = ScraperHealth(status="ok", error=None, listing_count=5)
        assert health.status == "ok"
        assert health.listing_count == 5
        with pytest.raises(dataclasses.FrozenInstanceError):
            health.listing_count = 0

    def test_run_counts(self):
        counts = RunCounts(total=10, new=3, price_drops=1, disappeared=2)
        assert counts.total == 10
        with pytest.raises(dataclasses.FrozenInstanceError):
            counts.total = 0

    def test_profile_run_result(self):
        started = datetime(2026, 9, 19, 8, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2026, 9, 19, 8, 5, 0, tzinfo=timezone.utc)
        result = ProfileRunResult(
            profile_id="praha7-byty",
            run_id="run-1",
            started_at=started,
            finished_at=finished,
            status="ok",
            scraper_health={"sreality": ScraperHealth(status="ok", error=None, listing_count=5)},
            counts=RunCounts(total=5, new=2, price_drops=0, disappeared=1),
        )
        assert result.profile_id == "praha7-byty"
        assert result.scraper_health["sreality"].listing_count == 5
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.status = "failed"
