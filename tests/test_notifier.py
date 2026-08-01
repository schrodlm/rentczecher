"""Tests for notifier rendering.

Run: python3 -m pytest tests/test_notifier.py -v
"""

from rentczecher.adapters.notifiers.smtp import _render_card
from rentczecher.adapters.scrapers.base import Listing


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


class TestMapsLinkLocation:
    """Maps links use the listing's own location; no city is ever appended."""

    def test_non_prague_maps_link_has_no_praha(self):
        listing = _make_listing(location="Nekvasovy, okres Plzeň-jih")
        html = _render_card(listing, is_rent=False)
        assert "maps.google.com" in html
        assert "Praha" not in html

    def test_prague_listing_still_gets_maps_link(self):
        listing = _make_listing(location="Umělecká, Praha - Holešovice")
        html = _render_card(listing, is_rent=True)
        assert "maps.google.com" in html
