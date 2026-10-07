"""Live integration tests for scrapers - hit real websites.

Excluded from the default pytest run. Run deliberately with:
python3 -m pytest -m live tests/live/test_scrapers.py -v
These tests hit real APIs so they may be slow and results change over time.
"""
import pytest

from rentczecher_engine.adapters.scrapers.client import build_client
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria
from tests.profiles import criteria, layouts

SEARCHES: dict[str, Criteria] = {
    "praha7-byty": criteria(max_price=25000, dispositions=layouts("2+kk", "3+kk")),
    "domazlice-domy": criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401),
                               max_price=5000000, min_land_m2=500),
}


@pytest.fixture(scope="module")
def client():
    with build_client() as c:
        yield c


def _scraper(cls, search_id: str, client):
    return cls(SEARCHES[search_id], client)


# ─── Sreality ───────────────────────────────────────────────

class TestSrealityLive:
    def test_praha7_returns_listings(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "praha7-byty", client)
        listings = s.scrape()
        # May be 0 transiently, but typically > 0
        assert isinstance(listings, list)

    def test_praha7_listings_have_required_fields(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "praha7-byty", client)
        listings = s.scrape()
        if not listings:
            pytest.skip("Sreality returned 0 listings (transient)")
        l = listings[0]
        assert l.id.startswith("sreality:")
        assert l.source == "sreality"
        assert l.price > 0
        assert l.url.startswith("https://www.sreality.cz/detail/")
        assert l.title

    def test_praha7_gps_extracted(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "praha7-byty", client)
        listings = s.scrape()
        if not listings:
            pytest.skip("Sreality returned 0 listings (transient)")
        with_gps = [l for l in listings if l.lat is not None]
        assert len(with_gps) > 0, "No listings have GPS coordinates"
        l = with_gps[0]
        assert 49.5 < l.lat < 50.5, f"Latitude {l.lat} out of Prague range"
        assert 14.0 < l.lon < 15.0, f"Longitude {l.lon} out of Prague range"

    def test_praha7_price_in_range(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "praha7-byty", client)
        listings = s.scrape()
        max_price = SEARCHES["praha7-byty"].max_price
        assert max_price is not None
        for l in listings:
            assert l.price <= max_price, f"Price {l.price} exceeds max {max_price}"

    def test_domazlice_returns_houses(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "domazlice-domy", client)
        listings = s.scrape()
        assert len(listings) > 0, "Domazlice should have house listings on Sreality"

    def test_domazlice_has_land_area(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "domazlice-domy", client)
        listings = s.scrape()
        assert len(listings) > 0, "No listings"
        with_land = [l for l in listings if l.land_m2 is not None]
        assert len(with_land) > 0, "No listings have land_m2 extracted"
        for l in with_land:
            assert l.land_m2 > 0

    def test_domazlice_prices_are_sale_range(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "domazlice-domy", client)
        listings = s.scrape()
        assert len(listings) > 0
        # Sale prices should be > 50k CZK (not monthly rent)
        for l in listings:
            assert l.price > 50000, f"Price {l.price} too low for sale - looks like rent"

    def test_domazlice_location_contains_domazlice(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "domazlice-domy", client)
        listings = s.scrape()
        assert len(listings) > 0
        with_domazlice = [l for l in listings if "Domažlice" in l.location_raw_text or "domažlice" in l.location_raw_text.lower()]
        assert len(with_domazlice) > 0, "No listings mention Domažlice in location"

    def test_first_detail_url_resolves(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        s = _scraper(SrealityScraper, "praha7-byty", client)
        listings = s.scrape()
        if not listings:
            pytest.skip("Sreality returned 0 listings (transient)")
        resp = client.get(listings[0].url)
        assert resp.status_code == 200, f"Constructed detail URL broken: {listings[0].url}"

    def test_pagination_collects_beyond_one_page(self, client):
        from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
        listings = SrealityScraper(criteria(), client).scrape()
        assert len(listings) > 100, f"Expected multi-page collection, got {len(listings)}"


# ─── Bezrealitky ────────────────────────────────────────────

class TestBezrealitkyLive:
    def test_praha7_returns_listings(self, client):
        from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
        s = _scraper(BezrealitkyScraper, "praha7-byty", client)
        listings = s.scrape()
        assert len(listings) > 0, "Bezrealitky should return Praha 7 rentals"

    def test_praha7_gps_and_charges(self, client):
        from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
        s = _scraper(BezrealitkyScraper, "praha7-byty", client)
        listings = s.scrape()
        assert len(listings) > 0
        with_gps = [l for l in listings if l.lat is not None]
        with_charges = [l for l in listings if l.charges is not None]
        assert len(with_gps) > 0, "No GPS from Bezrealitky"
        assert len(with_charges) > 0, "No charges from Bezrealitky"

    def test_praha7_listings_have_images(self, client):
        from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
        s = _scraper(BezrealitkyScraper, "praha7-byty", client)
        listings = s.scrape()
        assert len(listings) > 0
        with_img = [l for l in listings if l.image_url]
        assert len(with_img) > 0, "No listings have images"

    def test_praha7_dispositions_are_valid(self, client):
        from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
        s = _scraper(BezrealitkyScraper, "praha7-byty", client)
        listings = s.scrape()
        valid = {"1+kk", "1+1", "2+kk", "2+1", "3+kk", "3+1", "4+kk", "4+1", "5+kk", "5+1", "6+", "atypicky", "garsoniéra"}
        for l in listings:
            if l.disposition_raw_text:
                assert l.disposition_raw_text in valid, f"Unknown disposition: {l.disposition_raw_text}"

    def test_domazlice_returns_results(self, client):
        from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
        s = _scraper(BezrealitkyScraper, "domazlice-domy", client)
        listings = s.scrape()
        # May be 0-few for small district, just ensure no crash
        assert isinstance(listings, list)


# ─── RE/MAX ─────────────────────────────────────────────────

class TestRemaxLive:
    def test_praha7_returns_listings(self, client):
        from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
        s = _scraper(RemaxScraper, "praha7-byty", client)
        listings = s.scrape()
        assert len(listings) > 0, "RE/MAX should return Praha 7 rentals"

    def test_praha7_prices_valid(self, client):
        from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
        s = _scraper(RemaxScraper, "praha7-byty", client)
        listings = s.scrape()
        max_price = SEARCHES["praha7-byty"].max_price
        assert max_price is not None
        for l in listings:
            assert l.price > 0
            assert l.price <= max_price

    def test_praha7_titles_no_agent_id(self, client):
        from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
        s = _scraper(RemaxScraper, "praha7-byty", client)
        listings = s.scrape()
        for l in listings:
            assert "(ID " not in l.title, f"Agent ID in title: {l.title}"

    def test_praha7_location_normalized(self, client):
        from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
        s = _scraper(RemaxScraper, "praha7-byty", client)
        listings = s.scrape()
        for l in listings:
            assert "\n" not in l.location_raw_text, f"Newline in location: {repr(l.location_raw_text)}"
            assert "  " not in l.location_raw_text, f"Double space in location: {repr(l.location_raw_text)}"

    def test_domazlice_no_crash(self, client):
        from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
        s = _scraper(RemaxScraper, "domazlice-domy", client)
        listings = s.scrape()
        # Genuinely 0 results in Domazlice on RE/MAX - just ensure no crash
        assert isinstance(listings, list)
