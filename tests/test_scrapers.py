"""Offline scraper behavior tests — no network access.

Run: python3 -m pytest tests/test_scrapers.py -v
"""

import json
from pathlib import Path

import httpx
import pytest

from rentczecher.adapters.scrapers import bezrealitky, sreality
from rentczecher.adapters.scrapers.base import ScraperBrokenError
from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher.adapters.scrapers.client import build_client
from rentczecher.adapters.scrapers.remax import RemaxScraper
from rentczecher.adapters.scrapers.sreality import SrealityScraper

FIXTURES = Path(__file__).parent / "fixtures" / "sreality"


def _refusing_client() -> httpx.Client:
    def refuse(request):
        raise AssertionError(f"unexpected network request: {request.url}")

    return build_client(transport=httpx.MockTransport(refuse))

FLATS_PROFILE = {
    "search": {"min_price": 0, "max_price": 25000},
    "scrapers": {"sreality": {
        "enabled": True,
        "category_main_cb": 1,
        "category_type_cb": 2,
        "locality_district_id": 5007,
    }},
}

HOUSES_PROFILE = {
    "search": {"min_price": 0, "max_price": 5000000, "min_land_m2": 500},
    "scrapers": {"sreality": {
        "enabled": True,
        "category_main_cb": 2,
        "category_type_cb": 1,
        "locality_district_id": 8,
        "category_sub_cb": "37|43|44",
    }},
}


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


class TestScraperEnabledFlag:
    """A scraper whose config block is absent or lacks enabled:true never runs,
    even when instantiated directly."""

    def test_scrapers_are_disabled_by_default(self):
        profile = {"search": {"max_price": 25000}, "scrapers": {}}
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper):
            assert scraper_cls(profile, _refusing_client()).scrape() == [], scraper_cls.name


class TestRemaxUrlBuilding:
    """_build_url() substitutes min/max price into the config template."""

    def test_url_building(self):
        profile = {
            "search": {"min_price": 17000, "max_price": 25000},
            "scrapers": {"remax": {
                "enabled": True,
                "search_url": (
                    "https://www.remax-czech.cz/reality/vyhledavani/"
                    "?hledani=2&price_from={min_price}&price_to={max_price}"
                ),
            }},
        }
        url = RemaxScraper(profile, _refusing_client())._build_url()
        assert "price_from=17000" in url
        assert "price_to=25000" in url
        assert "{min_price}" not in url and "{max_price}" not in url


class TestSrealityDistrictConfig:
    """A sreality profile without locality_district_id logs an error and yields
    no results instead of another region's listings."""

    def test_missing_district_id_logs_error_and_returns_nothing(self, caplog):
        profile = {
            "search": {"max_price": 25000},
            "scrapers": {"sreality": {
                "enabled": True,
                "category_main_cb": 1,
                "category_type_cb": 2,
            }},
        }
        with caplog.at_level("ERROR", logger="rentczecher"):
            listings = SrealityScraper(profile, _refusing_client()).scrape()
        assert listings == []
        assert any("locality_district_id" in r.message for r in caplog.records)


class TestSrealitySearchParams:
    """Query params match the /api/v1/estates/search contract."""

    def test_flats_params(self):
        params = SrealityScraper(FLATS_PROFILE, _refusing_client())._build_params(offset=100)
        assert params["category_main_cb"] == 1
        assert params["category_type_cb"] == 2
        assert params["locality_district_id"] == 5007
        assert params["per_page"] == 100
        assert params["offset"] == 100
        assert "page" not in params
        assert params["lang"] == "cs"
        assert params["price_from"] == 0
        assert params["price_to"] == 25000
        assert "category_sub_cb" not in params
        assert "estate_area_from" not in params

    def test_sub_cb_is_repeated_param_not_pipe_string(self):
        params = SrealityScraper(HOUSES_PROFILE, _refusing_client())._build_params(offset=0)
        assert params["category_sub_cb"] == [37, 43, 44]

    def test_min_land_becomes_estate_area_from(self):
        params = SrealityScraper(HOUSES_PROFILE, _refusing_client())._build_params(offset=0)
        assert params["estate_area_from"] == 500


class TestSrealityParsing:
    """Fixture-driven parsing of recorded /api/v1/estates/search responses."""

    def _scrape_fixture(self, monkeypatch, fixture_name, profile):
        payload = json.loads((FIXTURES / fixture_name).read_text())
        client, calls = _serve_pages(monkeypatch, {0: payload})
        listings = SrealityScraper(profile, client).scrape()
        return listings, calls, payload

    def test_flats_fixture_parses_all_fields(self, monkeypatch):
        # The fixture holds three real listings; two exceed the profile's
        # 25000 price cap and must be dropped by the client-side filter.
        listings, calls, payload = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_PROFILE)
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
        assert l.url == "https://www.sreality.cz/detail/pronajem/byt/2+kk/praha-holesovice-u-vody/1222430796"
        assert l.image_url.startswith("https://")

    def test_houses_fixture_parses_land_and_district(self, monkeypatch):
        # One of the three fixture houses exceeds the 5M price cap.
        listings, _, _ = self._scrape_fixture(monkeypatch, "search_houses_domazlice.json", HOUSES_PROFILE)
        assert sorted(x.id for x in listings) == ["sreality:3870457932", "sreality:527867980"]
        l = next(x for x in listings if x.id == "sreality:527867980")
        assert l.disposition == "Rodinný"
        assert l.size_m2 == 142
        assert l.land_m2 == 728
        assert "Domažlice" in l.location
        assert l.url == "https://www.sreality.cz/detail/prodej/dum/rodinny/horsovsky-tyn-semosice/527867980"

    def test_city_equal_to_citypart_is_not_duplicated_in_location(self, monkeypatch):
        # Village listings often have city == citypart (Drahotín/Drahotín).
        listings, _, _ = self._scrape_fixture(monkeypatch, "search_houses_domazlice.json", HOUSES_PROFILE)
        l = next(x for x in listings if x.id == "sreality:3870457932")
        assert l.location == "Drahotín, Domažlice"

    def test_request_sends_browser_headers(self, monkeypatch):
        _, calls, _ = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_PROFILE)
        headers = calls[0].headers
        assert "Mozilla" in headers["User-Agent"]
        assert headers["Accept"] == "application/json"


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
        listings = SrealityScraper(FLATS_PROFILE, client).scrape()
        assert sorted(l.id for l in listings) == ["sreality:1", "sreality:2", "sreality:3"]
        assert [int(c.url.params["offset"]) for c in calls] == [0, 100]

    def test_stops_on_empty_page(self, monkeypatch):
        pages = {0: {"results": [self._estate(1)], "pagination": {"total": 99}}}
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_PROFILE, client).scrape()
        assert len(listings) == 1
        assert [int(c.url.params["offset"]) for c in calls] == [0, 100]

    def test_stops_when_server_repeats_results_instead_of_paginating(self, monkeypatch):
        # A server that re-serves the same listings for every offset must not
        # cause an endless crawl: no new hash_ids means stop.
        same = [self._estate(1), self._estate(2)]
        pages = {o: {"results": same, "pagination": {"total": 500}} for o in (0, 100, 200, 300)}
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_PROFILE, client).scrape()
        assert len(listings) == 2
        assert len(calls) == 2

    def test_price_outside_range_is_filtered_client_side(self, monkeypatch):
        pages = {0: {"results": [self._estate(1, price=20000), self._estate(2, price=99999)],
                     "pagination": {"total": 2}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_PROFILE, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_missing_disposition_never_produces_double_slash_url(self, monkeypatch):
        estate = self._estate(7)
        estate["category_sub_cb"] = None
        pages = {0: {"results": [estate], "pagination": {"total": 1}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_PROFILE, client).scrape()
        url = listings[0].url
        assert "//" not in url.removeprefix("https://")
        assert url.endswith("/praha-holesovice/7")


class TestSrealityContract:
    """A search response without the expected shape raises ScraperBrokenError
    instead of silently yielding zero results."""

    def test_unrecognized_response_shape_raises(self):
        def handler(request):
            return httpx.Response(200, json={"estates": []})

        client = build_client(transport=httpx.MockTransport(handler))
        with pytest.raises(ScraperBrokenError):
            SrealityScraper(FLATS_PROFILE, client).scrape()


BEZ_PROFILE = {
    "search": {"min_price": 0, "max_price": 25000},
    "scrapers": {"bezrealitky": {
        "enabled": True,
        "estate_type": "BYT",
        "offer_type": "PRONAJEM",
        "region_osm_id": "R20000064250",
    }},
}


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
        listings = BezrealitkyScraper(BEZ_PROFILE, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]
        l = listings[0]
        assert l.source == "bezrealitky"
        assert l.title == "Pronajem - 2+kk - 55 m2 - Veletržní, Praha 7"
        assert l.price == 20000
        assert l.location == "Veletržní, Praha 7"
        assert l.url == "https://www.bezrealitky.cz/nemovitosti-byty-domy/byt-1"
        assert l.image_url == "https://img.bezrealitky.cz/1.jpg"
        assert l.size_m2 == 55
        assert l.disposition == "2+kk"
        assert l.charges == 3500
        assert abs(l.lat - 50.1) < 1e-9
        assert abs(l.lon - 14.43) < 1e-9

    def test_reserved_and_out_of_range_adverts_are_skipped(self, monkeypatch):
        adverts = [
            _bez_advert(1),
            _bez_advert(2, reserved=True),
            _bez_advert(3, price=99999),
        ]
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page(adverts, total_count=3)})
        listings = BezrealitkyScraper(BEZ_PROFILE, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]

    def test_paginates_until_total_count(self, monkeypatch):
        first = [_bez_advert(i) for i in range(1, 16)]
        second = [_bez_advert(16)]
        client, calls = _serve_bez_pages(monkeypatch, {
            1: _bez_page(first, total_count=16),
            2: _bez_page(second, total_count=16),
        })
        listings = BezrealitkyScraper(BEZ_PROFILE, client).scrape()
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
        listings = BezrealitkyScraper(BEZ_PROFILE, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:16"]

    def test_missing_next_data_raises_scraper_broken(self, monkeypatch):
        client, _ = _serve_bez_pages(monkeypatch, {1: "<html><body>redesigned</body></html>"})
        with pytest.raises(ScraperBrokenError):
            BezrealitkyScraper(BEZ_PROFILE, client).scrape()
