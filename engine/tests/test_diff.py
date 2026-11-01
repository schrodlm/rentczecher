"""Tests for classifying a run's survivors into new, price-dropped and
updated.

Run: python3 -m pytest tests/test_diff.py -v
"""

from rentczecher_engine.domain.dedup import DedupOutcome, MatchBand, MatchScore, MergeDecision
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.services.diff import classify


def _make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="sreality:1", source="sreality", title="Pronájem bytu 2+kk 50 m²",
        price=20000, location_raw_text="Veletržní, Praha 7", url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


def _outcome(listings: list[Listing]) -> DedupOutcome:
    return DedupOutcome(survivors=listings, merges=(), uncertain=())


def _merged(keeper: Listing, absorbed: Listing) -> tuple[DedupOutcome, dict[str, Listing]]:
    merge = MergeDecision(keeper_id=keeper.id, absorbed_id=absorbed.id,
                          score=MatchScore(total=60.0, factors=(), band=MatchBand.MATCH))
    return DedupOutcome(survivors=[keeper], merges=(merge,), uncertain=()), {absorbed.id: absorbed}


def test_every_unseen_listing_is_reported_new_and_nothing_else():
    listings = [_make_listing(id="a"), _make_listing(id="b")]

    diff = classify(_outcome(listings), {}, seen_ids=set(), viewed_ids=set(), latest_prices={})

    assert [l.id for l in diff.new] == ["a", "b"]
    assert diff.price_drops == []


def test_a_lower_price_than_last_seen_is_reported_as_a_drop_carrying_the_old_price():
    listing = _make_listing(id="a", price=16000)

    diff = classify(_outcome([listing]), {}, seen_ids={"a"}, viewed_ids=set(), latest_prices={"a": 18000})

    assert diff.new == []
    assert len(diff.price_drops) == 1
    dropped = diff.price_drops[0]
    assert dropped.id == "a"
    assert dropped.price == 16000
    assert dropped.price_drop_from == 18000


def test_a_listing_new_this_run_is_never_also_reported_as_a_drop():
    listing = _make_listing(id="a", price=16000)

    diff = classify(_outcome([listing]), {}, seen_ids=set(), viewed_ids=set(), latest_prices={"a": 18000})

    assert [l.id for l in diff.new] == ["a"]
    assert diff.price_drops == []


def test_a_listing_with_no_recorded_price_is_never_reported_as_a_drop():
    listing = _make_listing(id="a", price=16000)

    diff = classify(_outcome([listing]), {}, seen_ids={"a"}, viewed_ids=set(), latest_prices={})

    assert diff.new == []
    assert diff.price_drops == []


def test_a_portal_newly_posting_a_viewed_flat_updates_it():
    outcome, located = _merged(_make_listing(id="a"), _make_listing(id="b", source="bezrealitky"))

    diff = classify(outcome, located, seen_ids={"a"}, viewed_ids={"a"}, latest_prices={"a": 20000})

    assert diff.updated_keeper_ids == {"a"}


def test_a_flat_is_updated_under_its_keeper_when_the_new_posting_keeps_it():
    outcome, located = _merged(_make_listing(id="b", source="bezrealitky"), _make_listing(id="a"))

    diff = classify(outcome, located, seen_ids={"a"}, viewed_ids={"a"}, latest_prices={"a": 20000})

    assert diff.updated_keeper_ids == {"b"}


def test_a_posting_landing_alone_on_a_viewed_flat_updates_it():
    listing = _make_listing(id="b", source="bezrealitky")

    diff = classify(_outcome([listing]), {}, seen_ids=set(), viewed_ids={"b"}, latest_prices={})

    assert diff.updated_keeper_ids == {"b"}


def test_a_price_rise_on_a_viewed_flat_updates_it():
    listing = _make_listing(id="a", price=22000)

    diff = classify(_outcome([listing]), {}, seen_ids={"a"}, viewed_ids={"a"}, latest_prices={"a": 20000})

    assert diff.updated_keeper_ids == {"a"}


def test_an_unchanged_viewed_flat_is_not_updated():
    listing = _make_listing(id="a", price=20000)

    diff = classify(_outcome([listing]), {}, seen_ids={"a"}, viewed_ids={"a"}, latest_prices={"a": 20000})

    assert diff.updated_keeper_ids == set()


def test_a_flat_never_viewed_is_not_updated_however_it_changed():
    outcome, located = _merged(_make_listing(id="a", price=18000), _make_listing(id="b", source="bezrealitky"))

    diff = classify(outcome, located, seen_ids={"a"}, viewed_ids=set(), latest_prices={"a": 20000})

    assert diff.updated_keeper_ids == set()


def test_a_viewed_flat_whose_posting_has_no_recorded_price_is_not_updated():
    listing = _make_listing(id="a", price=20000)

    diff = classify(_outcome([listing]), {}, seen_ids={"a"}, viewed_ids={"a"}, latest_prices={})

    assert diff.updated_keeper_ids == set()
