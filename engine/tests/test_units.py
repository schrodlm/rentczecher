"""Unit tests for scoring, dedup, and db modules.

Run with: python3 -m pytest tests/test_units.py -v
"""
from rentczecher_engine.adapters.scrapers.base import Listing


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test:1", source="test", title="Test", price=20000,
        location_raw_text="Praha 7 - Holešovice", url="https://example.com",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


# ─── Scoring ────────────────────────────────────────────────

class TestScoring:
    DISPOSITION_ONLY = {
        "scoring": {
            "disposition_weight": 100,
            "preferred_dispositions": ["1+kk", "2+kk"],
        },
    }

    RENTAL_PROFILE = {
        "scoring": {
            "price_per_m2_weight": 40,
            "disposition_weight": 30,
            "preferred_dispositions": ["2+kk", "2+1", "3+kk"],
            "size_weight": 15,
            "ideal_size_m2": 55,
            "neighborhood_weight": 15,
            "preferred_neighborhoods": ["Holešovice", "Letná", "Bubeneč"],
        }
    }

    HOUSE_PROFILE = {
        "scoring": {
            "land_weight": 40,
            "ideal_land_m2": 2000,
            "price_weight": 30,
            "max_good_price": 3000000,
            "size_weight": 30,
            "ideal_size_m2": 150,
        }
    }

    def test_good_rental_scores_high(self):
        from rentczecher_engine.services.score import compute_score
        l = _make_listing(price=20000, size_m2=50, disposition="2+kk")
        score = compute_score(l, self.RENTAL_PROFILE)
        assert score >= 70, f"Good rental should score 70+, got {score}"

    def test_bad_rental_scores_low(self):
        from rentczecher_engine.services.score import compute_score
        l = _make_listing(price=24000, size_m2=28, disposition="1+kk", location_raw_text="Praha 7")
        score = compute_score(l, self.RENTAL_PROFILE)
        assert score < 30, f"Bad rental should score <30, got {score}"

    def test_preferred_disposition_first_scores_highest(self):
        from rentczecher_engine.services.score import compute_score
        l1 = _make_listing(price=20000, size_m2=50, disposition="2+kk")
        l2 = _make_listing(price=20000, size_m2=50, disposition="3+kk")
        s1 = compute_score(l1, self.RENTAL_PROFILE)
        s2 = compute_score(l2, self.RENTAL_PROFILE)
        assert s1 > s2, "First preferred disposition should score higher"

    def test_no_size_doesnt_crash(self):
        from rentczecher_engine.services.score import compute_score
        l = _make_listing(disposition="2+kk")
        score = compute_score(l, self.RENTAL_PROFILE)
        assert isinstance(score, int)

    def test_no_disposition_doesnt_crash(self):
        from rentczecher_engine.services.score import compute_score
        l = _make_listing(size_m2=50)
        score = compute_score(l, self.RENTAL_PROFILE)
        assert isinstance(score, int)

    def test_empty_scoring_config_returns_zero(self):
        from rentczecher_engine.services.score import compute_score
        l = _make_listing()
        assert compute_score(l, {}) == 0
        assert compute_score(l, {"scoring": {}}) == 0

    def test_house_large_land_scores_high(self):
        from rentczecher_engine.services.score import compute_score
        l = _make_listing(price=2500000, size_m2=150, land_m2=2000)
        score = compute_score(l, self.HOUSE_PROFILE)
        assert score >= 80, f"House with ideal land/price/size should score 80+, got {score}"

    def test_house_small_land_scores_lower(self):
        from rentczecher_engine.services.score import compute_score
        l1 = _make_listing(price=3000000, size_m2=100, land_m2=2000)
        l2 = _make_listing(price=3000000, size_m2=100, land_m2=200)
        s1 = compute_score(l1, self.HOUSE_PROFILE)
        s2 = compute_score(l2, self.HOUSE_PROFILE)
        assert s1 > s2, "Larger land should score higher"

    def test_house_cheaper_scores_higher(self):
        from rentczecher_engine.services.score import compute_score
        l1 = _make_listing(price=1500000, size_m2=100, land_m2=1000)
        l2 = _make_listing(price=4500000, size_m2=100, land_m2=1000)
        s1 = compute_score(l1, self.HOUSE_PROFILE)
        s2 = compute_score(l2, self.HOUSE_PROFILE)
        assert s1 > s2, "Cheaper house should score higher"

    def test_score_is_0_to_100(self):
        from rentczecher_engine.services.score import compute_score
        for price in [5000, 20000, 50000]:
            for size in [20, 50, 100]:
                l = _make_listing(price=price, size_m2=size, disposition="2+kk")
                score = compute_score(l, self.RENTAL_PROFILE)
                assert 0 <= score <= 100, f"Score {score} out of range"

    def test_a_preferred_disposition_scores_by_its_rank(self):
        from rentczecher_engine.services.score import compute_score
        assert compute_score(_make_listing(disposition="1+kk"), self.DISPOSITION_ONLY) == 100
        assert compute_score(_make_listing(disposition="2+kk"), self.DISPOSITION_ONLY) == 80

    def test_disposition_preference_is_case_insensitive(self):
        from rentczecher_engine.services.score import compute_score
        assert compute_score(_make_listing(disposition="2+KK"), self.DISPOSITION_ONLY) == 80

    def test_a_studio_label_scores_as_not_preferred(self):
        """Scoring compares raw labels, so a garsoniéra is not a preferred 1+kk."""
        from rentczecher_engine.services.score import compute_score
        assert compute_score(_make_listing(disposition="garsoniéra"), self.DISPOSITION_ONLY) == 10

    def test_an_unparseable_disposition_scores_as_not_preferred(self):
        """An unparseable label scores like any disposition outside the list."""
        from rentczecher_engine.services.score import compute_score
        assert compute_score(_make_listing(disposition="Rodinný"), self.DISPOSITION_ONLY) == 10

    def test_a_missing_disposition_adds_nothing(self):
        from rentczecher_engine.services.score import compute_score
        assert compute_score(_make_listing(disposition=None), self.DISPOSITION_ONLY) == 0

    def test_a_late_preferred_rank_scores_no_lower_than_twenty(self):
        from rentczecher_engine.services.score import compute_score
        profile = {"scoring": {"disposition_weight": 100, "preferred_dispositions": [
            "1+kk", "1+1", "2+kk", "2+1", "3+kk", "3+1"]}}
        assert compute_score(_make_listing(disposition="3+kk"), profile) == 20
        assert compute_score(_make_listing(disposition="3+1"), profile) == 20

    def test_a_preferred_list_compares_its_raw_labels(self):
        """A garsoniéra in the preferred list does not stand for a 1+kk."""
        from rentczecher_engine.services.score import compute_score
        profile = {"scoring": {"disposition_weight": 100, "preferred_dispositions": ["garsoniéra", "1+kk"]}}
        assert compute_score(_make_listing(disposition="1+kk"), profile) == 80
