"""Edge-case tests for dedup, scoring, and db modules.

Run with: python3 -m pytest tests/test_edge_cases.py -v
"""
from rentczecher_engine.adapters.scrapers.base import Listing
from tests.profiles import preferences


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test:1", source="test", title="Test", price=20000,
        location_raw_text="Praha 7 - Holesovice", url="https://example.com",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


# ─── 7. Scoring with all zero weights ────────────────────────

class TestScoringAllZeroWeights:
    def test_all_zero_weights_returns_zero(self):
        from rentczecher_engine.services.score import compute_score

        listing = _make_listing(
            price=20000, size_m2=50, disposition_raw_text="2+kk",
            land_m2=500, location_raw_text="Praha 7 - Holesovice",
        )
        score = compute_score(listing, preferences())
        assert score == 0, f"All-zero weights should yield 0, got {score}"
