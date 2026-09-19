"""Tests for the tram-enrichment on/off decision.

Run: python3 -m pytest tests/test_enrich.py -v
"""

from rentczecher.domain.listing import Listing
from rentczecher.services.enrich import apply_tram_enrichment


def _listing(id="sreality:1"):
    return Listing.build(id=id, source="sreality", title="t", price=20000,
                         location="l", url="https://example.com/1")


def test_disabled_leaves_listings_untouched():
    calls = []

    def enrich(listing):
        calls.append(listing.id)
        return listing

    listings = [_listing()]
    result = apply_tram_enrichment(listings, False, enrich)

    assert result == listings
    assert calls == []


def test_enabled_runs_every_listing_through_the_injected_enrichment():
    calls = []

    def enrich(listing):
        calls.append(listing.id)
        return listing.with_annotations(nearest_stop="Vltavská")

    result = apply_tram_enrichment([_listing("sreality:1"), _listing("sreality:2")], True, enrich)

    assert calls == ["sreality:1", "sreality:2"]
    assert all(listing.nearest_stop == "Vltavská" for listing in result)
