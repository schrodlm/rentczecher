"""Edge-case tests for dedup, scoring, and db modules.

Run with: python3 -m pytest tests/test_edge_cases.py -v
"""
from rentczecher_engine.adapters.scrapers.base import Listing


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

        profile = {
            "scoring": {
                "price_per_m2_weight": 0,
                "disposition_weight": 0,
                "size_weight": 0,
                "neighborhood_weight": 0,
                "land_weight": 0,
                "price_weight": 0,
            }
        }
        listing = _make_listing(
            price=20000, size_m2=50, disposition_raw_text="2+kk",
            land_m2=500, location_raw_text="Praha 7 - Holesovice",
        )
        score = compute_score(listing, profile)
        assert score == 0, f"All-zero weights should yield 0, got {score}"

    def test_all_zero_weights_doesnt_crash(self):
        from rentczecher_engine.services.score import compute_score

        profile = {"scoring": {
            "price_per_m2_weight": 0,
            "disposition_weight": 0,
            "size_weight": 0,
            "neighborhood_weight": 0,
        }}
        listing = _make_listing()
        score = compute_score(listing, profile)
        assert isinstance(score, int)


# ─── 10. Config missing optional keys ────────────────────────

class TestConfigMissingOptionalKeys:
    """Scoring should not crash when preferred_dispositions,
    preferred_neighborhoods, etc. are missing from config."""

    def test_missing_preferred_dispositions(self):
        from rentczecher_engine.services.score import compute_score

        profile = {
            "scoring": {
                "disposition_weight": 30,
                # preferred_dispositions is MISSING
                "size_weight": 15,
                "ideal_size_m2": 55,
            }
        }
        listing = _make_listing(disposition_raw_text="2+kk", size_m2=50)
        score = compute_score(listing, profile)
        assert isinstance(score, int)

    def test_missing_preferred_neighborhoods(self):
        from rentczecher_engine.services.score import compute_score

        profile = {
            "scoring": {
                "neighborhood_weight": 15,
                # preferred_neighborhoods is MISSING
                "size_weight": 15,
                "ideal_size_m2": 55,
            }
        }
        listing = _make_listing(location_raw_text="Praha 7 - Holesovice", size_m2=50)
        score = compute_score(listing, profile)
        assert isinstance(score, int)

    def test_missing_ideal_size(self):
        from rentczecher_engine.services.score import compute_score

        profile = {
            "scoring": {
                "size_weight": 15,
                # ideal_size_m2 is MISSING (defaults to 55)
            }
        }
        listing = _make_listing(size_m2=50)
        score = compute_score(listing, profile)
        assert isinstance(score, int)

    def test_missing_max_good_price(self):
        from rentczecher_engine.services.score import compute_score

        profile = {
            "scoring": {
                "price_weight": 30,
                # max_good_price is MISSING (defaults to 3000000)
            }
        }
        listing = _make_listing(price=2500000)
        score = compute_score(listing, profile)
        assert isinstance(score, int)

    def test_completely_empty_scoring_section(self):
        from rentczecher_engine.services.score import compute_score

        listing = _make_listing(
            price=20000, size_m2=50, disposition_raw_text="2+kk",
            location_raw_text="Praha 7 - Holesovice",
        )
        # Empty scoring dict
        assert compute_score(listing, {"scoring": {}}) == 0
        # No scoring key at all
        assert compute_score(listing, {}) == 0

    def test_missing_ideal_land(self):
        from rentczecher_engine.services.score import compute_score

        profile = {
            "scoring": {
                "land_weight": 40,
                # ideal_land_m2 is MISSING (defaults to 2000)
            }
        }
        listing = _make_listing(land_m2=1500)
        score = compute_score(listing, profile)
        assert isinstance(score, int)
        assert score > 0
