"""Offline scraper behavior tests — no network access.

Run: python3 -m pytest tests/test_scrapers.py -v
"""

import json
from pathlib import Path

import httpx
import pytest

from rentczecher.adapters.scrapers import bezrealitky, remax, sreality
from rentczecher.adapters.scrapers.base import ScraperBrokenError
from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher.adapters.scrapers.bezrealitky import _parse_location as _bez_parse_location
from rentczecher.adapters.scrapers.client import build_client
from rentczecher.adapters.scrapers.location_resolver import PlaceNotFoundError
from rentczecher.adapters.scrapers.remax import RemaxScraper
from rentczecher.adapters.scrapers.remax import _parse_location as _remax_parse_location
from rentczecher.adapters.scrapers.sreality import SrealityScraper
from rentczecher.adapters.scrapers.sreality import _parse_location as _sreality_parse_location
from rentczecher.domain.location import ParsedPlace
from rentczecher.domain.search import SearchSpec

FIXTURES = Path(__file__).parent / "fixtures" / "sreality"


def _refusing_client() -> httpx.Client:
    def refuse(request):
        raise AssertionError(f"unexpected network request: {request.url}")

    return build_client(transport=httpx.MockTransport(refuse))

FLATS_SPEC = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7",
                        min_price=0, max_price=25000)

HOUSES_SPEC = SearchSpec(offer_type="sale", estate_type="house", place="domazlice",
                         min_price=0, max_price=5000000, min_land_m2=500)


def _serve_pages(monkeypatch, pages):
    """Serve canned JSON payloads keyed by offset through a MockTransport client."""
    calls = []

    def handler(request):
        calls.append(request)
        offset = int(request.url.params["offset"])
        payload = pages.get(offset, {"results": [], "pagination": {"total": 0}})
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(sreality.time, "sleep", lambda _: None)
    return build_client(transport=httpx.MockTransport(handler)), calls


class TestSrealitySearchParams:
    """Query params match the /api/v1/estates/search contract, derived from
    the spec and its resolved place."""

    def test_flats_params(self):
        params = SrealityScraper(FLATS_SPEC, _refusing_client())._build_params(offset=100)
        assert params["category_main_cb"] == 1
        assert params["category_type_cb"] == 2
        assert params["locality_district_id"] == 5007
        assert params["per_page"] == 100
        assert params["offset"] == 100
        assert "page" not in params
        assert params["lang"] == "cs"
        assert params["price_from"] == 0
        assert params["price_to"] == 25000
        assert "estate_area_from" not in params

    def test_min_land_becomes_estate_area_from(self):
        params = SrealityScraper(HOUSES_SPEC, _refusing_client())._build_params(offset=0)
        assert params["estate_area_from"] == 500


class TestSrealityParsing:
    """Fixture-driven parsing of recorded /api/v1/estates/search responses."""

    def _scrape_fixture(self, monkeypatch, fixture_name, spec):
        payload = json.loads((FIXTURES / fixture_name).read_text())
        client, calls = _serve_pages(monkeypatch, {0: payload})
        listings = SrealityScraper(spec, client).scrape()
        return listings, calls, payload

    def test_flats_fixture_parses_all_fields(self, monkeypatch):
        # The fixture holds three real listings; two exceed the profile's
        # 25000 price cap and must be dropped by the client-side filter.
        listings, calls, payload = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_SPEC)
        assert [x.id for x in listings] == ["sreality:1222430796"]
        l = listings[0]
        assert l.source == "sreality"
        assert l.title == payload["results"][0]["advert_name"]
        assert l.price == 19900
        assert isinstance(l.price, int)
        assert l.disposition == "2+kk"
        assert l.size_m2 == 56
        assert l.land_m2 is None
        assert abs(l.lat - 50.111328) < 1e-6
        assert abs(l.lon - 14.448094) < 1e-6
        assert l.location == "U Vody, Praha - Holešovice, Praha 7"
        assert l.parsed_place.names == ("U Vody", "Praha", "Holešovice", "Praha 7")
        assert l.parsed_place.district is None
        assert l.url == "https://www.sreality.cz/detail/pronajem/byt/2+kk/praha-holesovice-u-vody/1222430796"
        assert l.image_url.startswith("https://")

    def test_houses_fixture_parses_land_and_district(self, monkeypatch):
        # One of the three fixture houses exceeds the 5M price cap.
        listings, _, _ = self._scrape_fixture(monkeypatch, "search_houses_domazlice.json", HOUSES_SPEC)
        assert sorted(x.id for x in listings) == ["sreality:3870457932", "sreality:527867980"]
        l = next(x for x in listings if x.id == "sreality:527867980")
        assert l.disposition == "Rodinný"
        assert l.size_m2 == 142
        assert l.land_m2 == 728
        assert "Domažlice" in l.location
        assert l.url == "https://www.sreality.cz/detail/prodej/dum/rodinny/horsovsky-tyn-semosice/527867980"

    def test_city_equal_to_citypart_is_not_duplicated_in_location(self, monkeypatch):
        # Village listings often have city == citypart (Drahotín/Drahotín).
        listings, _, _ = self._scrape_fixture(monkeypatch, "search_houses_domazlice.json", HOUSES_SPEC)
        l = next(x for x in listings if x.id == "sreality:3870457932")
        assert l.location == "Drahotín, Domažlice"

    def test_request_sends_browser_headers(self, monkeypatch):
        _, calls, _ = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_SPEC)
        headers = calls[0].headers
        assert "Mozilla" in headers["User-Agent"]
        assert headers["Accept"] == "application/json"


class TestSrealityLocationParsing:
    """The locality dict's street/city/citypart/district keys all belong in
    names, deduped and in that order; the portal has no okres concept."""

    def test_full_locality(self):
        place = _sreality_parse_location({
            "street": "U Vody", "city": "Praha", "citypart": "Holešovice", "district": "Praha 7",
        })
        assert place.names == ("U Vody", "Praha", "Holešovice", "Praha 7")
        assert place.district is None

    def test_city_equal_to_citypart_is_deduped(self):
        place = _sreality_parse_location({"city": "Drahotín", "citypart": "Drahotín"})
        assert place.names == ("Drahotín",)
        assert place.district is None

    def test_empty_locality(self):
        assert _sreality_parse_location({}) == ParsedPlace()


class TestSrealityPagination:
    """Paging continues until the reported total is collected or a page is empty."""

    @staticmethod
    def _estate(hash_id, price=20000):
        return {
            "hash_id": hash_id,
            "advert_name": f"Pronájem bytu 2+kk 50 m² #{hash_id}",
            "price_czk": float(price),
            "category_sub_cb": {"name": "2+kk", "value": 4},
            "category_main_cb": {"name": "Byty", "value": 1},
            "category_type_cb": {"name": "Pronájem", "value": 2},
            "locality": {"city": "Praha", "citypart": "Holešovice", "district": "Praha 7",
                         "gps_lat": 50.1, "gps_lon": 14.4,
                         "city_seo_name": "praha", "citypart_seo_name": "holesovice"},
            "advert_images": ["//img.example/1.jpg"],
        }

    def test_collects_across_offsets_and_dedupes_hash_ids(self, monkeypatch):
        pages = {
            0: {"results": [self._estate(1), self._estate(2)], "pagination": {"total": 3}},
            100: {"results": [self._estate(2), self._estate(3)], "pagination": {"total": 3}},
        }
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_SPEC, client).scrape()
        assert sorted(l.id for l in listings) == ["sreality:1", "sreality:2", "sreality:3"]
        assert [int(c.url.params["offset"]) for c in calls] == [0, 100]

    def test_stops_on_empty_page(self, monkeypatch):
        pages = {0: {"results": [self._estate(1)], "pagination": {"total": 99}}}
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_SPEC, client).scrape()
        assert len(listings) == 1
        assert [int(c.url.params["offset"]) for c in calls] == [0, 100]

    def test_stops_when_server_repeats_results_instead_of_paginating(self, monkeypatch):
        # A server that re-serves the same listings for every offset must not
        # cause an endless crawl: no new hash_ids means stop.
        same = [self._estate(1), self._estate(2)]
        pages = {o: {"results": same, "pagination": {"total": 500}} for o in (0, 100, 200, 300)}
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_SPEC, client).scrape()
        assert len(listings) == 2
        assert len(calls) == 2

    def test_price_outside_range_is_filtered_client_side(self, monkeypatch):
        pages = {0: {"results": [self._estate(1, price=20000), self._estate(2, price=99999)],
                     "pagination": {"total": 2}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_SPEC, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_missing_disposition_never_produces_double_slash_url(self, monkeypatch):
        estate = self._estate(7)
        estate["category_sub_cb"] = None
        pages = {0: {"results": [estate], "pagination": {"total": 1}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_SPEC, client).scrape()
        url = listings[0].url
        assert "//" not in url.removeprefix("https://")
        assert url.endswith("/praha-holesovice/7")


class TestSrealityPlaceBasedParams:
    """With a resolved place, search params derive from the place and the
    spec's typed estate/offer types instead of raw portal codes."""

    def test_district_place_supplies_location_and_categories(self):
        spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7", max_price=25000)
        scraper = SrealityScraper(spec, _refusing_client())
        params = scraper._build_params(offset=0)
        assert params["locality_district_id"] == 5007
        assert "locality_region_id" not in params
        assert params["category_main_cb"] == 1
        assert params["category_type_cb"] == 2

    def test_kraj_place_searches_by_region(self):
        spec = SearchSpec(offer_type="sale", estate_type="house", place="plzensky", max_price=5000000)
        scraper = SrealityScraper(spec, _refusing_client())
        params = scraper._build_params(offset=0)
        assert params["locality_region_id"] == 2
        assert "locality_district_id" not in params
        assert params["category_main_cb"] == 2
        assert params["category_type_cb"] == 1



class TestSrealityContract:
    """A search response without the expected shape raises ScraperBrokenError
    instead of silently yielding zero results."""

    def test_unrecognized_response_shape_raises(self):
        def handler(request):
            return httpx.Response(200, json={"estates": []})

        client = build_client(transport=httpx.MockTransport(handler))
        with pytest.raises(ScraperBrokenError):
            SrealityScraper(FLATS_SPEC, client).scrape()


BEZ_SPEC = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7",
                      min_price=0, max_price=25000)


def _bez_advert(advert_id, price=20000, **overrides):
    advert = {
        "id": str(advert_id),
        "uri": f"byt-{advert_id}",
        "price": price,
        "reserved": False,
        "address": "Veletržní, Praha 7",
        "disposition": "DISP_2_KK",
        "surface": 55,
        "surfaceLand": None,
        "charges": 3500,
        "gps": {"lat": 50.1, "lng": 14.43},
        "mainImage": {"__ref": f"Image:{advert_id}"},
    }
    advert.update(overrides)
    return advert


def _bez_page(adverts, total_count):
    cache = {"listAdverts({})": {
        "list": [{"__ref": f"Advert:{a['id']}"} for a in adverts],
        "totalCount": total_count,
    }}
    for a in adverts:
        cache[f"Advert:{a['id']}"] = a
        cache[f"Image:{a['id']}"] = {"url": f"https://img.bezrealitky.cz/{a['id']}.jpg"}
    next_data = json.dumps({"props": {"pageProps": {"apolloCache": cache}}})
    return (f'<html><body><script id="__NEXT_DATA__" type="application/json">'
            f'{next_data}</script></body></html>')


def _serve_bez_pages(monkeypatch, pages):
    """Serve canned search-page HTML keyed by page number through MockTransport."""
    calls = []

    def handler(request):
        calls.append(request)
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, text=pages[page])

    monkeypatch.setattr(bezrealitky.time, "sleep", lambda _: None)
    return build_client(transport=httpx.MockTransport(handler)), calls


class TestBezrealitkyParsing:
    """Fixture-driven parsing of the search page's __NEXT_DATA__ Apollo cache."""

    def test_parses_advert_fields(self, monkeypatch):
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page([_bez_advert(1)], total_count=1)})
        listings = BezrealitkyScraper(BEZ_SPEC, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]
        l = listings[0]
        assert l.source == "bezrealitky"
        assert l.title == "Pronajem - 2+kk - 55 m2 - Veletržní, Praha 7"
        assert l.price == 20000
        assert l.location == "Veletržní, Praha 7"
        assert l.parsed_place.names == ("Veletržní", "Praha 7")
        assert l.parsed_place.district is None
        assert l.url == "https://www.bezrealitky.cz/nemovitosti-byty-domy/byt-1"
        assert l.image_url == "https://img.bezrealitky.cz/1.jpg"
        assert l.size_m2 == 55
        assert l.disposition == "2+kk"
        assert l.charges == 3500
        assert abs(l.lat - 50.1) < 1e-9
        assert abs(l.lon - 14.43) < 1e-9

    def test_undefined_disposition_is_treated_as_absent(self, monkeypatch):
        advert = _bez_advert(1, disposition="UNDEFINED")
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page([advert], total_count=1)})
        listings = BezrealitkyScraper(BEZ_SPEC, client).scrape()
        assert listings[0].disposition is None

    def test_reserved_and_out_of_range_adverts_are_skipped(self, monkeypatch):
        adverts = [
            _bez_advert(1),
            _bez_advert(2, reserved=True),
            _bez_advert(3, price=99999),
        ]
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page(adverts, total_count=3)})
        listings = BezrealitkyScraper(BEZ_SPEC, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]

    def test_paginates_until_total_count(self, monkeypatch):
        first = [_bez_advert(i) for i in range(1, 16)]
        second = [_bez_advert(16)]
        client, calls = _serve_bez_pages(monkeypatch, {
            1: _bez_page(first, total_count=16),
            2: _bez_page(second, total_count=16),
        })
        listings = BezrealitkyScraper(BEZ_SPEC, client).scrape()
        assert len(listings) == 16
        assert len(calls) == 2

    def test_page_of_only_filtered_adverts_still_advances_pagination(self, monkeypatch):
        # Filtering must not be mistaken for an empty portal page: adverts
        # were present, so the reported total still governs pagination.
        first = [_bez_advert(i, price=99999) for i in range(1, 16)]
        second = [_bez_advert(16)]
        client, _ = _serve_bez_pages(monkeypatch, {
            1: _bez_page(first, total_count=16),
            2: _bez_page(second, total_count=16),
        })
        listings = BezrealitkyScraper(BEZ_SPEC, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:16"]

    def test_missing_next_data_raises_scraper_broken(self, monkeypatch):
        client, _ = _serve_bez_pages(monkeypatch, {1: "<html><body>redesigned</body></html>"})
        with pytest.raises(ScraperBrokenError):
            BezrealitkyScraper(BEZ_SPEC, client).scrape()


class TestBezrealitkyLocationParsing:
    """The comma-separated address splits into names on both commas and
    'Praha - Bubeneč' style dash pairs; the portal has no okres concept."""

    def test_comma_separated_address(self):
        place = _bez_parse_location("Veletržní, Praha 7")
        assert place.names == ("Veletržní", "Praha 7")
        assert place.district is None

    def test_dash_pair_segment_splits_further(self):
        place = _bez_parse_location("U Studánky, Praha - Bubeneč")
        assert place.names == ("U Studánky", "Praha", "Bubeneč")
        assert place.district is None

    def test_empty_address(self):
        assert _bez_parse_location("") == ParsedPlace()


class TestBezrealitkyPlaceBasedParams:
    """With a resolved place, the search URL derives from the place and the
    spec's typed estate/offer types; without either a place or a configured
    region id the scraper refuses to run rather than search elsewhere."""

    def test_place_and_spec_drive_the_url(self):
        spec = SearchSpec(offer_type="sale", estate_type="house", place="domazlice", max_price=5000000)
        scraper = BezrealitkyScraper(spec, _refusing_client())
        url = scraper._build_url()
        assert "regionOsmIds=R441864" in url
        assert "estateType=DUM" in url
        assert "offerType=PRODEJ" in url
        assert "location=exact" in url


    def test_place_based_title_labels_follow_the_spec(self, monkeypatch):
        spec = SearchSpec(offer_type="sale", estate_type="house", place="domazlice", max_price=5000000)
        client, _ = _serve_bez_pages(monkeypatch, {
            1: _bez_page([_bez_advert(1, price=3000000)], total_count=1),
        })
        listings = BezrealitkyScraper(spec, client).scrape()
        assert listings[0].title.startswith("Prodej - ")


REMAX_SPEC = SearchSpec(offer_type="sale", estate_type="house", place="domazlice",
                        min_price=0, max_price=5000000)


def _remax_card(listing_id, price=3000000):
    return f"""
    <div class="pl-items__item" data-price="{price}" data-title="Prodej rodinného domu"
         data-display-address="Domažlice - Týnské Předměstí">
      <a href="/reality/detail/{listing_id}/prodej-domu">Prodej rodinného domu 4+kk 120 m², pozemek 800 m²</a>
      <img src="/img/{listing_id}.jpg">
      <span>4+kk 120 m² pozemek 800 m² 3 000 000 Kč</span>
    </div>"""


def _remax_page(cards, has_next=False):
    next_html = '<a rel="next" href="?stranka=2">další</a>' if has_next else ""
    return f"<html><body>{''.join(cards)}{next_html}</body></html>"


def _serve_remax_pages(monkeypatch, pages):
    """Serve canned search-page HTML keyed by stranka number through MockTransport."""
    calls = []

    def handler(request):
        calls.append(request)
        page = int(request.url.params.get("stranka", "1"))
        return httpx.Response(200, text=pages[page])

    monkeypatch.setattr(remax.time, "sleep", lambda _: None)
    return build_client(transport=httpx.MockTransport(handler)), calls


class TestRemaxLocationParsing:
    """The card's address string splits into names and the okres it states
    (the bare-name slot before the kraj holds a district, never a town);
    the actual town rides at the tail of the card title."""

    def test_title_town_joins_the_names(self):
        place = _remax_parse_location(
            "Dlouhá 2534 / 2534, Cheb , Karlovarský kraj",
            "Prodej bytu 2+1 v osobním vlastnictví 60 m², Aš")
        assert place.names == ("Dlouhá 2534 / 2534", "Aš")
        assert place.district == "Cheb"

    def test_title_town_equal_to_the_okres_means_the_capital(self):
        place = _remax_parse_location(
            "Mírová 2024 / 2024, Cheb , Karlovarský kraj",
            "Pronájem bytu 1+1 v osobním vlastnictví 38 m², Cheb")
        assert place.names == ("Mírová 2024 / 2024", "Cheb")
        assert place.district is None

    def test_bare_address_still_gets_the_title_town(self):
        place = _remax_parse_location(
            "Kladno , Středočeský kraj", "Prodej domu 250 m², Královice")
        assert place.names == ("Královice",)
        assert place.district == "Kladno"

    def test_commaless_title_adds_nothing(self):
        place = _remax_parse_location("Domažlice - Týnské Předměstí",
                                      "Prodej rodinného domu")
        assert place.names == ("Týnské Předměstí",)
        assert place.district == "Domažlice"

    def test_digit_bearing_title_tail_is_ignored(self):
        place = _remax_parse_location("Vinohradská 12, Praha 2",
                                      "Prodej bytu 2+kk 45 m², Praha 2")
        assert place.names == ("Vinohradská 12", "Praha 2")
        assert place.district is None

    def test_street_and_okres(self):
        place = _remax_parse_location("Škarmanská 369 / 369, Domažlice, Plzeňský kraj", "")
        assert place.names == ("Škarmanská 369 / 369",)
        assert place.district == "Domažlice"

    def test_bare_okres(self):
        place = _remax_parse_location("Domažlice, Plzeňský kraj", "")
        assert place.names == ()
        assert place.district == "Domažlice"

    def test_okres_with_part(self):
        place = _remax_parse_location("Domažlice - Týnské Předměstí", "")
        assert place.names == ("Týnské Předměstí",)
        assert place.district == "Domažlice"

    def test_okres_only_name(self):
        place = _remax_parse_location("Školní 853, Brno-venkov, Jihomoravský kraj", "")
        assert place.names == ("Školní 853",)
        assert place.district == "Brno-venkov"

    def test_praha_city_district_is_not_an_okres(self):
        place = _remax_parse_location("Vinohradská 12, Praha 2", "")
        assert place.names == ("Vinohradská 12", "Praha 2")
        assert place.district is None

    def test_bare_praha_is_not_an_okres(self):
        place = _remax_parse_location("Praha", "")
        assert place.names == ("Praha",)
        assert place.district is None

    def test_empty_location(self):
        assert _remax_parse_location("", "") == ParsedPlace()


class TestRemaxParsing:
    """Fixture-driven parsing of search result cards."""

    def test_parses_card_fields(self, monkeypatch):
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([_remax_card(12345)])})
        listings = RemaxScraper(REMAX_SPEC, client).scrape()
        assert [l.id for l in listings] == ["remax:12345"]
        l = listings[0]
        assert l.source == "remax"
        assert l.title == "Prodej rodinného domu"
        assert l.price == 3000000
        assert l.location == "Domažlice - Týnské Předměstí"
        # The portal's bare-name slot holds the okres, not the town.
        assert l.parsed_place.district == "Domažlice"
        assert l.parsed_place.names == ("Týnské Předměstí",)
        assert l.url == "https://www.remax-czech.cz/reality/detail/12345/prodej-domu"
        assert l.image_url == "https://www.remax-czech.cz/img/12345.jpg"
        assert l.size_m2 == 120
        assert l.land_m2 == 800
        assert l.disposition == "4+kk"

    def test_paginates_while_next_link_exists(self, monkeypatch):
        client, calls = _serve_remax_pages(monkeypatch, {
            1: _remax_page([_remax_card(1)], has_next=True),
            2: _remax_page([_remax_card(2)]),
        })
        listings = RemaxScraper(REMAX_SPEC, client).scrape()
        assert sorted(l.id for l in listings) == ["remax:1", "remax:2"]
        assert len(calls) == 2

    def test_page_without_cards_yields_nothing(self, monkeypatch):
        # A cardless page also means genuinely-zero results, so unlike the
        # other portals it cannot raise ScraperBrokenError.
        client, _ = _serve_remax_pages(monkeypatch, {1: "<html><body>žádné výsledky</body></html>"})
        assert RemaxScraper(REMAX_SPEC, client).scrape() == []

    def test_out_of_range_price_is_filtered(self, monkeypatch):
        cards = [_remax_card(1), _remax_card(2, price=99000000)]
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page(cards)})
        listings = RemaxScraper(REMAX_SPEC, client).scrape()
        assert [l.id for l in listings] == ["remax:1"]


class TestRemaxPlaceBasedUrl:
    """With a resolved place the search URL is built from the place and the
    spec's typed estate/offer types; the hand-pasted search_url becomes
    unnecessary."""

    def test_district_place_builds_the_full_url(self):
        spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7",
                          min_price=17000, max_price=25000)
        scraper = RemaxScraper(spec, _refusing_client())
        url = scraper._build_url()
        assert url.startswith("https://www.remax-czech.cz/reality/vyhledavani/?")
        assert "hledani=2" in url
        assert "types%5B4%5D=on" in url
        assert "regions%5B19%5D%5B78%5D=on" in url
        assert "price_from=17000" in url and "price_to=25000" in url

    def test_sale_house_maps_types_and_hledani(self):
        spec = SearchSpec(offer_type="sale", estate_type="house", place="domazlice", max_price=5000000)
        url = RemaxScraper(spec, _refusing_client())._build_url()
        assert "hledani=1" in url
        assert "types%5B6%5D=on" in url
        assert "regions%5B43%5D%5B3401%5D=on" in url
        assert "price_from" not in url

    def test_kraj_place_checks_every_district_of_the_region(self):
        spec = SearchSpec(offer_type="sale", estate_type="house", place="plzensky")
        url = RemaxScraper(spec, _refusing_client())._build_url()
        assert url.count("regions%5B43%5D") == 7
        assert "regions%5B43%5D%5B3401%5D=on" in url


class TestEstateOfferTypeCoverage:
    """Every schema Literal estate/offer value has a portal mapping in every
    scraper - a valid spec can never KeyError at scrape time."""

    @pytest.mark.parametrize("estate_type", ["flat", "house", "land", "cottage"])
    @pytest.mark.parametrize("offer_type", ["rent", "sale"])
    def test_every_combination_builds_portal_params(self, estate_type, offer_type):
        spec = SearchSpec(offer_type=offer_type, estate_type=estate_type,
                          place="praha-7", max_price=25000)
        SrealityScraper(spec, _refusing_client())._build_params(offset=0)
        BezrealitkyScraper(spec, _refusing_client())._build_url()
        RemaxScraper(spec, _refusing_client())._build_url()


class TestNarrowPlaceViews:
    """Each scraper narrows the resolved place to its own typed view at
    construction and holds no other portal's data afterwards."""

    def test_sreality_view_carries_only_sreality_fields(self):
        from rentczecher.adapters.scrapers.location_resolver import resolve
        from rentczecher.adapters.scrapers.sreality import SrealityPlace
        view = SrealityPlace.from_params(resolve("praha-7"))
        assert view == SrealityPlace(district_id=5007, region_id=10)

    def test_bezrealitky_view_carries_only_its_region_id(self):
        from rentczecher.adapters.scrapers.location_resolver import resolve
        from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyPlace
        view = BezrealitkyPlace.from_params(resolve("domazlice"))
        assert view == BezrealitkyPlace(region_id="R441864")

    def test_remax_view_tells_the_single_region_truth(self):
        from rentczecher.adapters.scrapers.location_resolver import resolve
        from rentczecher.adapters.scrapers.remax import RemaxPlace
        assert RemaxPlace.from_params(resolve("domazlice")) == RemaxPlace(
            region_id=43, district_ids=(3401,))
        kraj = RemaxPlace.from_params(resolve("plzensky"))
        assert kraj.region_id == 43 and len(kraj.district_ids) == 7

    def test_scrapers_hold_no_full_place_params(self):
        from rentczecher.adapters.scrapers.location_resolver import PlaceParams
        spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7", max_price=25000)
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper):
            scraper = scraper_cls(spec, _refusing_client())
            assert not any(isinstance(value, PlaceParams)
                           for value in vars(scraper).values()), scraper_cls.name


class TestPlaceResolutionFailure:
    """A scraper built for an unresolvable place raises PlaceNotFoundError
    instead of silently searching nowhere."""

    def test_unknown_slug_raises_at_construction(self):
        spec = SearchSpec(offer_type="rent", estate_type="flat",
                          place="not-a-real-place", max_price=25000)
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper):
            with pytest.raises(PlaceNotFoundError):
                scraper_cls(spec, _refusing_client())
