"""Offline scraper behavior tests — no network access.

Run: python3 -m pytest tests/test_scrapers.py -v
"""

import json
from importlib.metadata import version
from pathlib import Path
from typing import get_args

import httpx
import pytest

from rentczecher_engine.adapters.scrapers import ALL_SCRAPERS, bezrealitky, idnes, remax, sreality
from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher_engine.adapters.scrapers.client import build_client
from rentczecher_engine.adapters.scrapers.idnes import IdnesScraper
from rentczecher_engine.adapters.scrapers.parsing import parse_comma_separated_address
from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
from rentczecher_engine.adapters.scrapers.remax import _parse_location as _remax_parse_location
from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
from rentczecher_engine.adapters.scrapers.sreality import _parse_location as _sreality_parse_location
from rentczecher_engine.domain.errors import PlaceNotFoundError, ScraperBrokenError
from rentczecher_engine.domain.location import ParsedPlace, PlaceRef
from rentczecher_engine.domain.profile import Criteria, Portal

FIXTURES = Path(__file__).parent / "fixtures" / "sreality"


def _refusing_client() -> httpx.Client:
    def refuse(request):
        raise AssertionError(f"unexpected network request: {request.url}")

    return build_client(transport=httpx.MockTransport(refuse))

FLATS_CRITERIA = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78),
                          max_price=25000)

HOUSES_CRITERIA = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401),
                           max_price=5000000, min_land_m2=500)


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
    the criteria and its resolved place."""

    def test_flats_params(self):
        params = SrealityScraper(FLATS_CRITERIA, _refusing_client())._build_params(offset=100)
        assert params["category_main_cb"] == 1
        assert params["category_type_cb"] == 2
        assert params["locality_district_id"] == 5007
        assert params["per_page"] == 100
        assert params["offset"] == 100
        assert "page" not in params
        assert params["lang"] == "cs"
        assert "price_from" not in params
        assert params["price_to"] == 25000
        assert "estate_area_from" not in params

    def test_min_land_becomes_estate_area_from(self):
        params = SrealityScraper(HOUSES_CRITERIA, _refusing_client())._build_params(offset=0)
        assert params["estate_area_from"] == 500

    def test_no_price_bounds_send_no_price_params(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        params = SrealityScraper(criteria, _refusing_client())._build_params(offset=0)
        assert "price_from" not in params
        assert "price_to" not in params

    def test_min_price_alone_is_sent_without_a_max(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), min_price=15000)
        params = SrealityScraper(criteria, _refusing_client())._build_params(offset=0)
        assert params["price_from"] == 15000
        assert "price_to" not in params


class TestSrealityParsing:
    """Fixture-driven parsing of /api/v1/estates/search responses, made up in the
    shape the portal answers with."""

    def _scrape_fixture(self, monkeypatch, fixture_name, criteria):
        payload = json.loads((FIXTURES / fixture_name).read_text())
        client, calls = _serve_pages(monkeypatch, {0: payload})
        listings = SrealityScraper(criteria, client).scrape()
        return listings, calls, payload

    def test_flats_fixture_parses_all_fields(self, monkeypatch):
        # The fixture holds three listings; two exceed the profile's
        # 25000 price cap and must be dropped by the client-side filter.
        listings, calls, payload = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_CRITERIA)
        assert [x.id for x in listings] == ["sreality:910000001"]
        l = listings[0]
        assert l.source == "sreality"
        assert l.title == payload["results"][0]["advert_name"]
        assert l.price == 19900
        assert isinstance(l.price, int)
        assert l.disposition_raw_text == "2+kk"
        assert l.size_m2 == 56
        assert l.land_m2 is None
        assert abs(l.lat - 50.105) < 1e-6
        assert abs(l.lon - 14.44) < 1e-6
        assert l.location_raw_text == "U Vody, Praha - Holešovice, Praha 7"
        assert l.parsed_place.names == ("U Vody", "Praha", "Holešovice", "Praha 7")
        assert l.parsed_place.district is None
        assert l.url == "https://www.sreality.cz/detail/pronajem/byt/2+kk/praha-holesovice-u-vody/910000001"
        assert l.photo_urls[0].startswith("https://")
        assert not l.gallery_on_advert_page

    def test_a_listing_carries_its_whole_gallery_in_the_portals_order(self, monkeypatch):
        listings, _, payload = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_CRITERIA)
        gallery = payload["results"][0]["advert_images_all"]
        assert listings[0].photo_urls == tuple(
            f"https:{image['advert_image_sdn_url']}{sreality.PHOTO_PRESET}" for image in gallery)

    def test_a_listing_without_a_gallery_carries_no_photos(self, monkeypatch):
        payload = json.loads((FIXTURES / "search_flats_praha7.json").read_text())
        del payload["results"][0]["advert_images_all"]
        client, _ = _serve_pages(monkeypatch, {0: payload})
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert listings[0].photo_urls == ()

    def test_houses_fixture_parses_land_and_district(self, monkeypatch):
        # One of the three fixture houses exceeds the 5M price cap.
        listings, _, _ = self._scrape_fixture(monkeypatch, "search_houses_domazlice.json", HOUSES_CRITERIA)
        assert sorted(x.id for x in listings) == ["sreality:920000001", "sreality:920000003"]
        l = next(x for x in listings if x.id == "sreality:920000001")
        assert l.disposition_raw_text == "Rodinný"
        assert l.size_m2 == 142
        assert l.land_m2 == 728
        assert "Domažlice" in l.location_raw_text
        assert l.url == "https://www.sreality.cz/detail/prodej/dum/rodinny/horsovsky-tyn-semosice/920000001"

    def test_city_equal_to_citypart_is_not_duplicated_in_location(self, monkeypatch):
        # Village listings often have city == citypart (Drahotín/Drahotín).
        listings, _, _ = self._scrape_fixture(monkeypatch, "search_houses_domazlice.json", HOUSES_CRITERIA)
        l = next(x for x in listings if x.id == "sreality:920000003")
        assert l.location_raw_text == "Drahotín, Domažlice"

    def test_request_names_the_app_at_its_package_version(self, monkeypatch):
        _, calls, _ = self._scrape_fixture(monkeypatch, "search_flats_praha7.json", FLATS_CRITERIA)
        headers = calls[0].headers
        assert headers["User-Agent"] == f"rentczecher/{version('rentczecher_engine')} (+https://rentczecher.cz)"
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

    def test_housenumber_is_popisne_and_streetnumber_is_orientacni(self):
        place = _sreality_parse_location({"housenumber": "1401", "streetnumber": "5"})
        assert place.cislo_popisne == "1401"
        assert place.cislo_orientacni == "5"

    def test_null_or_empty_house_numbers_are_unknown(self):
        place = _sreality_parse_location({"housenumber": None, "streetnumber": ""})
        assert place.cislo_popisne is None
        assert place.cislo_orientacni is None


class TestSrealityPagination:
    """Paging continues until the reported total is collected or a page is empty."""

    @staticmethod
    def _estate(hash_id, price=20000):
        return {
            "hash_id": hash_id,
            "advert_name": f"Pronájem bytu 2+kk 50 m² #{hash_id}",
            "price_czk": float(price),
            "price_summary_czk": float(price),
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
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["sreality:1", "sreality:2", "sreality:3"]
        assert [int(c.url.params["offset"]) for c in calls] == [0, 100]

    def test_stops_on_empty_page(self, monkeypatch):
        pages = {0: {"results": [self._estate(1)], "pagination": {"total": 99}}}
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert len(listings) == 1
        assert [int(c.url.params["offset"]) for c in calls] == [0, 100]

    def test_stops_when_server_repeats_results_instead_of_paginating(self, monkeypatch):
        # A server that re-serves the same listings for every offset must not
        # cause an endless crawl: no new hash_ids means stop.
        same = [self._estate(1), self._estate(2)]
        pages = {o: {"results": same, "pagination": {"total": 500}} for o in (0, 100, 200, 300)}
        client, calls = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert len(listings) == 2
        assert len(calls) == 2

    def test_price_outside_range_is_filtered_client_side(self, monkeypatch):
        pages = {0: {"results": [self._estate(1, price=20000), self._estate(2, price=99999)],
                     "pagination": {"total": 2}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_skips_an_estate_whose_price_is_on_request(self, monkeypatch):
        on_request = {**self._estate(2, price=0), "price_note": "Info u realitního specialisty"}
        pages = {0: {"results": [self._estate(1), on_request], "pagination": {"total": 2}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_prices_a_plot_priced_per_m2_by_its_whole_property_summary(self, monkeypatch):
        plot = {**self._estate(1), "price_czk": 17200.0, "price_summary_czk": 11369200.0}
        criteria = Criteria(offer_type="sale", estate_type="land", place=PlaceRef("obvod", 78))
        pages = {0: {"results": [plot], "pagination": {"total": 1}}}
        client, _ = _serve_pages(monkeypatch, pages)
        (listing,) = SrealityScraper(criteria, client).scrape()
        assert listing.price == 11369200

    def test_skips_an_estate_priced_at_a_token_crown(self, monkeypatch):
        pages = {0: {"results": [self._estate(1), self._estate(2, price=1)], "pagination": {"total": 2}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_min_price_alone_drops_cheaper_estates(self, monkeypatch):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), min_price=15000)
        pages = {0: {"results": [self._estate(1, price=20000), self._estate(2, price=9000)],
                     "pagination": {"total": 2}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(criteria, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_unset_max_price_keeps_expensive_estates(self, monkeypatch):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        pages = {0: {"results": [self._estate(1, price=99999999)], "pagination": {"total": 1}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(criteria, client).scrape()
        assert [l.id for l in listings] == ["sreality:1"]

    def test_missing_disposition_never_produces_double_slash_url(self, monkeypatch):
        estate = self._estate(7)
        estate["category_sub_cb"] = None
        pages = {0: {"results": [estate], "pagination": {"total": 1}}}
        client, _ = _serve_pages(monkeypatch, pages)
        listings = SrealityScraper(FLATS_CRITERIA, client).scrape()
        url = listings[0].url
        assert "//" not in url.removeprefix("https://")
        assert url.endswith("/praha-holesovice/7")


class TestSrealityPlaceBasedParams:
    """With a resolved place, search params derive from the place and the
    typed estate/offer types of the criteria instead of raw portal codes."""

    def test_district_place_supplies_location_and_categories(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), max_price=25000)
        scraper = SrealityScraper(criteria, _refusing_client())
        params = scraper._build_params(offset=0)
        assert params["locality_district_id"] == 5007
        assert "locality_region_id" not in params
        assert params["category_main_cb"] == 1
        assert params["category_type_cb"] == 2

    def test_kraj_place_searches_by_region(self):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("kraj", 43), max_price=5000000)
        scraper = SrealityScraper(criteria, _refusing_client())
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
            SrealityScraper(FLATS_CRITERIA, client).scrape()


BEZ_CRITERIA = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78),
                        max_price=25000)


def _bez_advert(advert_id, price=20000, **overrides):
    advert = {
        "id": str(advert_id),
        "uri": f"byt-{advert_id}",
        "price": price,
        "currency": "CZK",
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
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]
        l = listings[0]
        assert l.source == "bezrealitky"
        assert l.title == "Pronajem - 2+kk - 55 m2 - Veletržní, Praha 7"
        assert l.price == 20000
        assert l.location_raw_text == "Veletržní, Praha 7"
        assert l.parsed_place.names == ("Veletržní", "Praha 7")
        assert l.parsed_place.district is None
        assert l.url == "https://www.bezrealitky.cz/nemovitosti-byty-domy/byt-1"
        assert l.photo_urls == ("https://img.bezrealitky.cz/1.jpg",)
        assert l.gallery_on_advert_page
        assert l.size_m2 == 55
        assert l.disposition_raw_text == "2+kk"
        assert l.charges == 3500
        assert abs(l.lat - 50.1) < 1e-9
        assert abs(l.lon - 14.43) < 1e-9

    def test_undefined_disposition_is_treated_as_absent(self, monkeypatch):
        advert = _bez_advert(1, disposition="UNDEFINED")
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page([advert], total_count=1)})
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert listings[0].disposition_raw_text is None

    def test_reserved_and_out_of_range_adverts_are_skipped(self, monkeypatch):
        adverts = [
            _bez_advert(1),
            _bez_advert(2, reserved=True),
            _bez_advert(3, price=99999),
        ]
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page(adverts, total_count=3)})
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]

    def test_skips_an_advert_priced_in_another_currency(self, monkeypatch):
        adverts = [_bez_advert(1), _bez_advert(2, price=1210, currency="EUR")]
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page(adverts, total_count=2)})
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]

    def test_unset_max_price_keeps_expensive_adverts(self, monkeypatch):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        adverts = [_bez_advert(1, price=99999999)]
        client, _ = _serve_bez_pages(monkeypatch, {1: _bez_page(adverts, total_count=1)})
        listings = BezrealitkyScraper(criteria, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:1"]

    def test_paginates_until_total_count(self, monkeypatch):
        first = [_bez_advert(i) for i in range(1, 16)]
        second = [_bez_advert(16)]
        client, calls = _serve_bez_pages(monkeypatch, {
            1: _bez_page(first, total_count=16),
            2: _bez_page(second, total_count=16),
        })
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
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
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["bezrealitky:16"]

    def test_missing_next_data_raises_scraper_broken(self, monkeypatch):
        client, _ = _serve_bez_pages(monkeypatch, {1: "<html><body>redesigned</body></html>"})
        with pytest.raises(ScraperBrokenError):
            BezrealitkyScraper(BEZ_CRITERIA, client).scrape()


def _bez_advert_page(public_images):
    next_data = json.dumps({"props": {"pageProps": {"origAdvert": {"id": "1", "publicImages": public_images}}}})
    return (f'<html><body><script id="__NEXT_DATA__" type="application/json">'
            f'{next_data}</script></body></html>')


class TestBezrealitkyAdvertGallery:
    """The whole gallery from the advert page's __NEXT_DATA__."""

    def test_lists_every_photo_in_the_pages_order(self):
        page = _bez_advert_page([{"url": "https://img.bezrealitky.cz/a.jpg"}, {"url": "https://img.bezrealitky.cz/b.jpg"}])
        assert bezrealitky.gallery_from_advert_page(page) == (
            "https://img.bezrealitky.cz/a.jpg", "https://img.bezrealitky.cz/b.jpg")

    def test_lists_a_photo_once_and_skips_one_without_a_url(self):
        page = _bez_advert_page([{"url": "https://img.bezrealitky.cz/a.jpg"}, {"url": None},
                                 {"url": "https://img.bezrealitky.cz/a.jpg"}])
        assert bezrealitky.gallery_from_advert_page(page) == ("https://img.bezrealitky.cz/a.jpg",)

    def test_an_advert_without_photos_has_none(self):
        assert bezrealitky.gallery_from_advert_page(_bez_advert_page([])) == ()

    def test_skips_a_photo_whose_url_is_not_text(self):
        page = _bez_advert_page([{"url": {"src": "x"}}, {"url": "https://img.bezrealitky.cz/a.jpg"}])
        assert bezrealitky.gallery_from_advert_page(page) == ("https://img.bezrealitky.cz/a.jpg",)

    @pytest.mark.parametrize("page", [
        "<html><body>no hydration blob</body></html>",
        '<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {}}}</script>',
        '<script id="__NEXT_DATA__" type="application/json">{"props": null}</script>',
        '<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": null}}</script>',
        '<script id="__NEXT_DATA__" type="application/json">[1, 2]</script>',
        '<script id="__NEXT_DATA__" type="application/json">{not json</script>',
    ])
    def test_a_page_of_another_shape_is_broken(self, page):
        with pytest.raises(ScraperBrokenError):
            bezrealitky.gallery_from_advert_page(page)


class TestBezrealitkyPagination:
    """Paging stops on the portal's own end, a page served again, or the page
    cap, judging repeats by the adverts a page carries before filtering."""

    def test_stops_at_the_page_cap_and_says_so(self, monkeypatch, caplog):
        pages = {page: _bez_page([_bez_advert(page)], total_count=10_000) for page in range(1, 60)}
        client, calls = _serve_bez_pages(monkeypatch, pages)
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert len(calls) == bezrealitky.MAX_PAGES
        assert len(listings) == bezrealitky.MAX_PAGES
        assert "pagination cap" in caplog.text

    def test_stops_when_the_portal_serves_the_same_page_again(self, monkeypatch):
        same = _bez_page([_bez_advert(1), _bez_advert(2)], total_count=10_000)
        client, calls = _serve_bez_pages(monkeypatch, {page: same for page in range(1, 60)})
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["bezrealitky:1", "bezrealitky:2"]
        assert len(calls) == 2

    def test_reads_on_past_a_page_whose_adverts_are_all_filtered_out(self, monkeypatch):
        client, calls = _serve_bez_pages(monkeypatch, {
            1: _bez_page([_bez_advert(1)], total_count=45),
            2: _bez_page([_bez_advert(2, currency="EUR")], total_count=45),
            3: _bez_page([_bez_advert(3)], total_count=45),
        })
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["bezrealitky:1", "bezrealitky:3"]
        assert len(calls) == 3

    def test_reads_on_when_an_advert_shifts_onto_the_next_page(self, monkeypatch):
        # A new advert posted between two pages pushes page 1's last advert
        # onto page 2, where the rest is filtered out.
        client, calls = _serve_bez_pages(monkeypatch, {
            1: _bez_page([_bez_advert(1)], total_count=45),
            2: _bez_page([_bez_advert(1), _bez_advert(2, currency="EUR")], total_count=45),
            3: _bez_page([_bez_advert(3)], total_count=45),
        })
        listings = BezrealitkyScraper(BEZ_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["bezrealitky:1", "bezrealitky:3"]
        assert len(calls) == 3


class TestCommaSeparatedAddressParsing:
    """The comma-separated address splits into names on both commas and
    'Praha - Bubeneč' style dash pairs. An 'okres X' segment states the
    district."""

    def test_comma_separated_address(self):
        place = parse_comma_separated_address("Veletržní, Praha 7")
        assert place.names == ("Veletržní", "Praha 7")
        assert place.district is None

    def test_dash_pair_segment_splits_further(self):
        place = parse_comma_separated_address("U Studánky, Praha - Bubeneč")
        assert place.names == ("U Studánky", "Praha", "Bubeneč")
        assert place.district is None

    def test_empty_address(self):
        assert parse_comma_separated_address("") == ParsedPlace()

    def test_an_okres_segment_states_the_district(self):
        place = parse_comma_separated_address("Nekvasovy, okres Plzeň-jih")
        assert place.names == ("Nekvasovy",)
        assert place.district == "Plzeň-jih"


class TestBezrealitkyPlaceBasedParams:
    """With a resolved place, the search URL derives from the place and the
    typed estate/offer types of the criteria; without either a place or a
    configured region id the scraper refuses to run rather than search
    elsewhere."""

    def test_place_and_criteria_drive_the_url(self):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401), max_price=5000000)
        scraper = BezrealitkyScraper(criteria, _refusing_client())
        url = scraper._build_url()
        assert "regionOsmIds=R441864" in url
        assert "estateType=DUM" in url
        assert "offerType=PRODEJ" in url
        assert "location=exact" in url

    def test_price_bounds_become_price_from_and_price_to(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78),
                            min_price=17000, max_price=25000)
        url = BezrealitkyScraper(criteria, _refusing_client())._build_url()
        assert "priceFrom=17000" in url
        assert "priceTo=25000" in url

    def test_no_price_bounds_send_no_price_params(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
        url = BezrealitkyScraper(criteria, _refusing_client())._build_url()
        assert "priceFrom" not in url
        assert "priceTo" not in url

    def test_place_based_title_labels_follow_the_criteria(self, monkeypatch):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401), max_price=5000000)
        client, _ = _serve_bez_pages(monkeypatch, {
            1: _bez_page([_bez_advert(1, price=3000000)], total_count=1),
        })
        listings = BezrealitkyScraper(criteria, client).scrape()
        assert listings[0].title.startswith("Prodej - ")


REMAX_CRITERIA = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401),
                          max_price=5000000)


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


def _remax_advert_page(hrefs):
    main = (f'<a id="mainImage" class="gallery__main-img-inner" data-fancybox="images" href="{hrefs[0]}"></a>'
            if hrefs else "")
    items = "".join(f'<a class="gallery__item" data-fancybox="images" href="{href}"><img src="{href}_th350"></a>'
                    for href in hrefs[1:])
    return (f'<html><body><div class="gallery">{main}'
            f'<div class="gallery__items">{items}</div></div></body></html>')


class TestRemaxAdvertGallery:
    """The whole gallery from the links of the advert page's gallery."""

    def test_lists_every_full_size_photo_in_the_pages_order(self):
        page = _remax_advert_page(["https://mlsf.remax-czech.cz/data/1/a.png", "https://mlsf.remax-czech.cz/data/1/b.jpg"])
        assert remax.gallery_from_advert_page(page) == (
            "https://mlsf.remax-czech.cz/data/1/a.png", "https://mlsf.remax-czech.cz/data/1/b.jpg")

    def test_lists_the_main_photo_first_and_once(self):
        page = _remax_advert_page(["https://mlsf.remax-czech.cz/data/1/a.png"] * 2)
        assert remax.gallery_from_advert_page(page) == ("https://mlsf.remax-czech.cz/data/1/a.png",)

    def test_resolves_a_relative_link(self):
        page = _remax_advert_page(["/data/1/a.png"])
        assert remax.gallery_from_advert_page(page) == ("https://www.remax-czech.cz/data/1/a.png",)

    def test_a_gallery_without_links_has_no_photos(self):
        assert remax.gallery_from_advert_page(_remax_advert_page([])) == ()

    def test_leaves_out_links_outside_the_gallery(self):
        page = _remax_advert_page(["https://mlsf.remax-czech.cz/data/1/a.png"]).replace(
            "</body>", '<a data-fancybox="images" href="https://mlsf.remax-czech.cz/data/2/similar.png"></a></body>')
        assert remax.gallery_from_advert_page(page) == ("https://mlsf.remax-czech.cz/data/1/a.png",)

    def test_a_page_without_a_gallery_is_broken(self):
        with pytest.raises(ScraperBrokenError):
            remax.gallery_from_advert_page("<html><body>no gallery</body></html>")


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

    def test_a_repeated_house_number_is_the_cislo_popisne_alone(self):
        place = _remax_parse_location("U smaltovny 1419 / 1419, Praha 7", "Pronájem bytu 2+kk")
        assert place.cislo_popisne == "1419"
        assert place.cislo_orientacni is None

    def test_two_different_house_numbers_are_popisne_then_orientacni(self):
        place = _remax_parse_location("Veletržní 1401 / 5a, Praha 7", "Pronájem bytu 2+kk")
        assert place.cislo_popisne == "1401"
        assert place.cislo_orientacni == "5a"

    def test_a_lone_number_is_no_house_number(self):
        place = _remax_parse_location("Vinohradská 12, Praha 2", "")
        assert place.cislo_popisne is None
        assert place.cislo_orientacni is None

    def test_street_and_okres(self):
        place = _remax_parse_location("Škarmanská 369 / 369, Domažlice, Plzeňský kraj", "")
        assert place.names == ("Škarmanská 369 / 369",)
        assert place.district == "Domažlice"

    def test_bare_okres(self):
        place = _remax_parse_location("Domažlice, Plzeňský kraj", "")
        assert place.names == ()
        assert place.district == "Domažlice"

    def test_kraj_vysocina_is_skipped_like_any_kraj(self):
        place = _remax_parse_location("Žďár nad Sázavou , Kraj Vysočina", "")
        assert place.names == ()
        assert place.district == "Žďár nad Sázavou"

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

    def test_a_praha_street_is_a_name_not_a_district(self):
        place = _remax_parse_location("Rybná , Hlavní město Praha , Praha 1, Hlavní město Praha", "")
        assert place.names == ("Rybná", "Praha 1")
        assert place.district is None

    def test_a_praha_mestska_cast_is_a_name_not_a_district(self):
        place = _remax_parse_location("Hlavní město Praha , Praha-Slivenec, Hlavní město Praha", "")
        assert place.names == ("Praha-Slivenec",)
        assert place.district is None

    def test_empty_location(self):
        assert _remax_parse_location("", "") == ParsedPlace()


class TestRemaxParsing:
    """Fixture-driven parsing of search result cards."""

    def test_parses_card_fields(self, monkeypatch):
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([_remax_card(12345)])})
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["remax:12345"]
        l = listings[0]
        assert l.source == "remax"
        assert l.title == "Prodej rodinného domu"
        assert l.price == 3000000
        assert l.location_raw_text == "Domažlice - Týnské Předměstí"
        # The portal's bare-name slot holds the okres, not the town.
        assert l.parsed_place.district == "Domažlice"
        assert l.parsed_place.names == ("Týnské Předměstí",)
        assert l.url == "https://www.remax-czech.cz/reality/detail/12345/prodej-domu"
        assert l.photo_urls == ("https://www.remax-czech.cz/img/12345.jpg",)
        assert l.gallery_on_advert_page
        assert l.size_m2 == 120
        assert l.land_m2 == 800
        assert l.disposition_raw_text == "4+kk"

    def test_paginates_while_next_link_exists(self, monkeypatch):
        client, calls = _serve_remax_pages(monkeypatch, {
            1: _remax_page([_remax_card(1)], has_next=True),
            2: _remax_page([_remax_card(2)]),
        })
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["remax:1", "remax:2"]
        assert len(calls) == 2

    def test_page_without_cards_yields_nothing(self, monkeypatch):
        # A cardless page also means genuinely-zero results, so unlike the
        # other portals it cannot raise ScraperBrokenError.
        client, _ = _serve_remax_pages(monkeypatch, {1: "<html><body>žádné výsledky</body></html>"})
        assert RemaxScraper(REMAX_CRITERIA, client).scrape() == []

    def test_reads_a_formatted_price_without_the_district_before_it(self, monkeypatch):
        card = '''
        <div class="pl-items__item" data-price="4&#160;750&#160;000&#160;Kč&#10;<small>(za měsíc)</small>"
             data-title="Prodej rodinného domu" data-display-address="Domažlice - Týnské Předměstí">
          <a href="/reality/detail/7/prodej-domu">Prodej rodinného domu 120 m²</a>
          <span>městská část Domažlice 3 4 750 000 Kč</span>
        </div>'''
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([card])})
        (listing,) = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert listing.price == 4750000

    @staticmethod
    def _priced_card(listing_id, data_price, title="Prodej pozemku 662 m², Domažlice"):
        return f'''
        <div class="pl-items__item" data-price="{data_price}" data-title="{title}" data-display-address="Domažlice">
          <a href="/reality/detail/{listing_id}/prodej">{title}</a>
        </div>'''

    def test_prices_a_plot_priced_per_m2_for_its_whole_area(self, monkeypatch):
        card = self._priced_card(9, "1&#160;200&#160;Kč <small>(za m²)</small>")
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([card])})
        (listing,) = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert listing.price == 794400

    def test_skips_a_price_stated_per_year(self, monkeypatch):
        card = self._priced_card(10, "120&#160;000&#160;Kč <small>(za rok)</small>")
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([card])})
        assert RemaxScraper(REMAX_CRITERIA, client).scrape() == []

    def test_reads_a_monthly_price_with_vat(self, monkeypatch):
        card = self._priced_card(11, "45&#160;000&#160;Kč <small>(vč. DPH, za měsíc)</small>")
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([card])})
        (listing,) = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert listing.price == 45000

    def test_skips_a_card_without_a_price_field(self, monkeypatch):
        card = '''
        <div class="pl-items__item" data-title="Prodej rodinného domu" data-display-address="Domažlice">
          <a href="/reality/detail/8/prodej-domu">Prodej rodinného domu 120 m²</a>
          <span>Domažlice 3 4 750 000 Kč</span>
        </div>'''
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([card])})
        assert RemaxScraper(REMAX_CRITERIA, client).scrape() == []

    def test_out_of_range_price_is_filtered(self, monkeypatch):
        cards = [_remax_card(1), _remax_card(2, price=99000000)]
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page(cards)})
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert [l.id for l in listings] == ["remax:1"]

    def test_unset_max_price_keeps_expensive_cards(self, monkeypatch):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401))
        client, _ = _serve_remax_pages(monkeypatch, {1: _remax_page([_remax_card(1, price=99000000)])})
        listings = RemaxScraper(criteria, client).scrape()
        assert [l.id for l in listings] == ["remax:1"]


class TestRemaxPagination:
    """Paging stops on the last page, a page served again, or the page cap,
    judging repeats by the cards a page carries before filtering."""

    def test_stops_at_the_page_cap_and_says_so(self, monkeypatch, caplog):
        pages = {page: _remax_page([_remax_card(page)], has_next=True) for page in range(1, 60)}
        client, calls = _serve_remax_pages(monkeypatch, pages)
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert len(calls) == remax.MAX_PAGES
        assert len(listings) == remax.MAX_PAGES
        assert "pagination cap" in caplog.text

    def test_stops_when_the_portal_serves_the_same_page_again(self, monkeypatch):
        same = _remax_page([_remax_card(1), _remax_card(2)], has_next=True)
        client, calls = _serve_remax_pages(monkeypatch, {page: same for page in range(1, 60)})
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["remax:1", "remax:2"]
        assert len(calls) == 2

    def test_reads_on_past_a_page_whose_cards_are_all_filtered_out(self, monkeypatch):
        client, calls = _serve_remax_pages(monkeypatch, {
            1: _remax_page([_remax_card(1)], has_next=True),
            2: _remax_page([_remax_card(2, price=9000000)], has_next=True),
            3: _remax_page([_remax_card(3)]),
        })
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["remax:1", "remax:3"]
        assert len(calls) == 3

    def test_reads_on_when_a_card_shifts_onto_the_next_page(self, monkeypatch):
        client, calls = _serve_remax_pages(monkeypatch, {
            1: _remax_page([_remax_card(1)], has_next=True),
            2: _remax_page([_remax_card(1), _remax_card(2, price=9000000)], has_next=True),
            3: _remax_page([_remax_card(3)]),
        })
        listings = RemaxScraper(REMAX_CRITERIA, client).scrape()
        assert sorted(l.id for l in listings) == ["remax:1", "remax:3"]
        assert len(calls) == 3


class TestRemaxPlaceBasedUrl:
    """With a resolved place the search URL is built from the place and the
    typed estate/offer types of the criteria; the hand-pasted search_url
    becomes unnecessary."""

    def test_district_place_builds_the_full_url(self):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78),
                            min_price=17000, max_price=25000)
        scraper = RemaxScraper(criteria, _refusing_client())
        url = scraper._build_url()
        assert url.startswith("https://www.remax-czech.cz/reality/vyhledavani/?")
        assert "hledani=1" in url
        assert "sale=2" in url
        assert "types%5B4%5D=on" in url
        assert "regions%5B19%5D%5B78%5D=on" in url
        assert "price_from=17000" in url and "price_to=25000" in url

    def test_sale_house_maps_types_and_the_sale_field(self):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401), max_price=5000000)
        url = RemaxScraper(criteria, _refusing_client())._build_url()
        assert "sale=1" in url
        assert "types%5B6%5D=on" in url
        assert "regions%5B43%5D%5B3401%5D=on" in url
        assert "price_from" not in url

    def test_no_price_bounds_send_no_price_params(self):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("okres", 3401))
        url = RemaxScraper(criteria, _refusing_client())._build_url()
        assert "price_from" not in url
        assert "price_to" not in url

    def test_kraj_place_checks_every_district_of_the_region(self):
        criteria = Criteria(offer_type="sale", estate_type="house", place=PlaceRef("kraj", 43))
        url = RemaxScraper(criteria, _refusing_client())._build_url()
        assert url.count("regions%5B43%5D") == 7
        assert "regions%5B43%5D%5B3401%5D=on" in url


def _idnes_id(n):
    return f"{n:024x}"


def _idnes_card(n, title="bytu 2+kk 54\xa0m²", price="18 500 Kč/měsíc", info="Vymyšlená, Plzeň - Doubravka",
                photo=True):
    listing_id = _idnes_id(n)
    photo_html = (f'<img class="image-preloading" data-src="https://img.example/{listing_id}.webp" alt="">'
                  if photo else "")
    return f"""
    <div class="grid__cell"><div class="c-products__item"><div id="snippet-s-result-article-{listing_id}"><article>
      <div class="c-products__inner">
        <a href="https://reality.idnes.cz/detail/pronajem/byt/plzen-vymyslena/{listing_id}/"
           data-brand="Vymyšlená realitní kancelář" class="c-products__link">
          <span class="c-products__imgs"><span class="c-products__img" style="background-image: url('bg.webp')">
            {photo_html}
            <span class="c-products__service"><img src="https://img.example/agency-logo.webp"
              class="c-products__service-img"></span>
          </span></span>
          <div class="c-products__content">
            <h2 class="c-products__title">
<span class="text-capitalize">pronájem</span>
{title}
            </h2>
            <p class="c-products__info">
              {info}
            </p>
            <div class="c-products__footer"><p class="c-products__price"><strong>{price}</strong></p></div>
          </div>
        </a>
      </div>
    </article></div></div></div>"""


_IDNES_AD_TILE = ('<div class="c-products__item c-products__item-advertisment">'
                  '<a href="https://ads.example/click">Reklama</a></div>')


def _idnes_page(cards, next_page=None):
    next_html = (f'<p class="paginator"><a class="btn paging__item next" href="/s/pronajem/byty/plzen/?page={next_page}">'
                 'Další</a></p>' if next_page is not None else "")
    return (f'<html><body><div class="c-products__list grid">{_IDNES_AD_TILE}{"".join(cards)}</div>'
            f'{next_html}</body></html>')


def _serve_idnes_pages(monkeypatch, pages):
    """Serve canned search pages keyed by the 0-based page parameter. The
    search form's own request is redirected to the results' URL, as the
    portal does."""
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/s/":
            return httpx.Response(301, headers={"Location": "https://reality.idnes.cz/s/pronajem/byty/plzen/"})
        page = int(request.url.params.get("page", "0"))
        return httpx.Response(200, text=pages[page])

    monkeypatch.setattr(idnes.time, "sleep", lambda _: None)
    return build_client(transport=httpx.MockTransport(handler)), calls


IDNES_CRITERIA = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("okres", 3405),
                          min_price=10000, max_price=25000)


class TestIdnesSearchUrl:
    """The search form's query names the offer, estate type, the search
    area by its RÚIAN code and a price ceiling, and never a URL robots.txt
    rules out."""

    def test_flat_rental_in_an_okres(self):
        url = IdnesScraper(IDNES_CRITERIA, _refusing_client())._build_url()
        assert url.startswith("https://reality.idnes.cz/s/?")
        assert "f%5Boffer%5D=lease" in url
        assert "f%5Btype%5D=flat" in url
        assert "f%5Blocality%5D=OKRES-3405" in url
        assert "f%5BpriceMax%5D=25000" in url

    @pytest.mark.parametrize(("place", "locality"), [
        (PlaceRef("kraj", 43), "VUSC-43"),
        (PlaceRef("obvod", 78), "MOP-78"),
        (PlaceRef("obec", 554791), "OKRES-3405"),
    ], ids=["kraj", "obvod", "obec searches its okres"])
    def test_the_search_area_names_the_locality(self, place, locality):
        criteria = Criteria(offer_type="sale", estate_type="house", place=place)
        assert f"f%5Blocality%5D={locality}" in IdnesScraper(criteria, _refusing_client())._build_url()

    @pytest.mark.parametrize(("estate_type", "subtype"), [("house", "house"), ("cottage", "cabin")])
    def test_houses_and_cottages_are_subtypes_of_houses(self, estate_type, subtype):
        criteria = Criteria(offer_type="sale", estate_type=estate_type, place=PlaceRef("okres", 3401))
        url = IdnesScraper(criteria, _refusing_client())._build_url()
        assert "f%5Btype%5D=house" in url
        assert f"f%5BsubtypeHouse%5D%5B%5D={subtype}" in url

    def test_never_builds_a_url_robots_txt_disallows(self):
        url = IdnesScraper(IDNES_CRITERIA, _refusing_client())._build_url()
        assert "priceMin" not in url
        assert "sort" not in url
        assert "%7C" not in url and "|" not in url

    def test_no_price_bounds_send_no_price_params(self):
        criteria = Criteria(offer_type="sale", estate_type="land", place=PlaceRef("okres", 3401))
        assert "price" not in IdnesScraper(criteria, _refusing_client())._build_url()


class TestIdnesParsing:
    """Each result card becomes a listing. Cards without a whole price, or
    outside the price range, are skipped."""

    def _scrape(self, monkeypatch, cards, criteria=IDNES_CRITERIA):
        client, _ = _serve_idnes_pages(monkeypatch, {0: _idnes_page(cards)})
        return IdnesScraper(criteria, client).scrape()

    def test_parses_every_field_of_a_flat_card(self, monkeypatch):
        listing, = self._scrape(monkeypatch, [_idnes_card(1)])
        assert listing.id == f"idnes:{_idnes_id(1)}"
        assert listing.source == "idnes"
        assert listing.title == "Pronájem bytu 2+kk 54 m²"
        assert listing.price == 18500
        assert listing.location_raw_text == "Vymyšlená, Plzeň - Doubravka"
        assert listing.parsed_place.names == ("Vymyšlená", "Plzeň", "Doubravka")
        assert listing.url == f"https://reality.idnes.cz/detail/pronajem/byt/plzen-vymyslena/{_idnes_id(1)}/"
        assert listing.photo_urls == (f"https://img.example/{_idnes_id(1)}.webp",)
        assert listing.gallery_on_advert_page
        assert listing.scraped.size_m2 == 54
        assert listing.scraped.land_m2 is None
        assert listing.scraped.disposition_raw_text == "2+kk"

    def test_a_house_gives_its_size_and_land_with_grouped_digits(self, monkeypatch):
        listing, = self._scrape(monkeypatch, [_idnes_card(
            1, title="domu 352\xa0m² s pozemkem 1\xa0255\xa0m²", price="19 000 Kč/měsíc")])
        assert listing.scraped.size_m2 == 352
        assert listing.scraped.land_m2 == 1255

    def test_a_plain_space_after_the_disposition_does_not_group_digits(self, monkeypatch):
        listing, = self._scrape(monkeypatch, [_idnes_card(1, title="bytu 3+1 120\xa0m²")])
        assert listing.scraped.size_m2 == 120
        assert listing.scraped.disposition_raw_text == "3+1"

    def test_a_plot_area_is_its_land(self, monkeypatch):
        criteria = Criteria(offer_type="sale", estate_type="land", place=PlaceRef("okres", 3401))
        listing, = self._scrape(monkeypatch, [_idnes_card(
            1, title="stavebního pozemku 1\xa0104\xa0m²", price="3 050 000 Kč")], criteria)
        assert listing.scraped.land_m2 == 1104
        assert listing.scraped.size_m2 is None
        assert listing.price == 3050000

    def test_a_room_has_no_disposition(self, monkeypatch):
        listing, = self._scrape(monkeypatch, [_idnes_card(1, title="pokoje 18\xa0m²", price="12 000 Kč/měsíc")])
        assert listing.scraped.disposition_raw_text is None
        assert listing.scraped.size_m2 == 18

    @pytest.mark.parametrize("price", ["Cena na vyžádání", "18 500 Kč/rok", "18 500 €"])
    def test_skips_a_card_without_a_whole_price(self, monkeypatch, price):
        assert self._scrape(monkeypatch, [_idnes_card(1, price=price)]) == []

    @pytest.mark.parametrize("price", ["9 900 Kč/měsíc", "25 001 Kč/měsíc"])
    def test_skips_a_card_outside_the_price_range(self, monkeypatch, price):
        assert self._scrape(monkeypatch, [_idnes_card(1, price=price)]) == []

    def test_an_unset_max_price_keeps_expensive_cards(self, monkeypatch):
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("okres", 3405))
        listings = self._scrape(monkeypatch, [_idnes_card(1, price="95 000 Kč/měsíc")], criteria)
        assert [listing.price for listing in listings] == [95000]

    def test_an_okres_in_the_address_states_the_district(self, monkeypatch):
        listing, = self._scrape(monkeypatch, [_idnes_card(1, info="Vymyšlov, okres Plzeň-Jih")])
        assert listing.parsed_place.names == ("Vymyšlov",)
        assert listing.parsed_place.district == "Plzeň-Jih"

    def test_reads_neither_ad_tiles_nor_similar_offers(self, monkeypatch):
        similar = (f'<div class="grid-similar-offers"><article class="c-grid-products__item">'
                   f'<a class="c-grid-products__inner" href="https://reality.idnes.cz/detail/prodej/byt/'
                   f'jinde/{_idnes_id(9)}/">Podobná nabídka</a></article></div>')
        page = f"<html><body>{_IDNES_AD_TILE}{similar}</body></html>"
        client, _ = _serve_idnes_pages(monkeypatch, {0: page})
        assert IdnesScraper(IDNES_CRITERIA, client).scrape() == []

    def test_a_card_without_a_photo_ignores_the_agency_logo(self, monkeypatch):
        listing, = self._scrape(monkeypatch, [_idnes_card(1, photo=False)])
        assert listing.photo_urls == ()


class TestIdnesPagination:
    """Paging follows the portal's own next link, stopping on the last page,
    a page served again, or the page cap."""

    def test_follows_the_next_link_until_there_is_none(self, monkeypatch):
        client, calls = _serve_idnes_pages(monkeypatch, {
            0: _idnes_page([_idnes_card(1)], next_page=1),
            1: _idnes_page([_idnes_card(2)], next_page=2),
            2: _idnes_page([_idnes_card(3)]),
        })
        scraper = IdnesScraper(IDNES_CRITERIA, client)
        listings = scraper.scrape()
        assert sorted(listing.id for listing in listings) == [f"idnes:{_idnes_id(n)}" for n in (1, 2, 3)]
        assert [str(call.url) for call in calls] == [
            scraper._build_url(),
            "https://reality.idnes.cz/s/pronajem/byty/plzen/",
            "https://reality.idnes.cz/s/pronajem/byty/plzen/?page=1",
            "https://reality.idnes.cz/s/pronajem/byty/plzen/?page=2",
        ]

    def test_stops_when_the_portal_serves_the_same_page_again(self, monkeypatch):
        same = _idnes_page([_idnes_card(1), _idnes_card(2)], next_page=1)
        client, calls = _serve_idnes_pages(monkeypatch, {0: same, 1: same})
        assert len(IdnesScraper(IDNES_CRITERIA, client).scrape()) == 2
        assert len(calls) == 3

    def test_reads_on_past_a_page_whose_cards_are_all_filtered_out(self, monkeypatch):
        client, _ = _serve_idnes_pages(monkeypatch, {
            0: _idnes_page([_idnes_card(1)], next_page=1),
            1: _idnes_page([_idnes_card(2, price="Cena na vyžádání")], next_page=2),
            2: _idnes_page([_idnes_card(3)]),
        })
        listings = IdnesScraper(IDNES_CRITERIA, client).scrape()
        assert sorted(listing.id for listing in listings) == [f"idnes:{_idnes_id(n)}" for n in (1, 3)]

    def test_a_card_that_moves_onto_the_next_page_keeps_its_first_reading(self, monkeypatch):
        client, _ = _serve_idnes_pages(monkeypatch, {
            0: _idnes_page([_idnes_card(1, price="18 000 Kč/měsíc")], next_page=1),
            1: _idnes_page([_idnes_card(1, price="17 000 Kč/měsíc"), _idnes_card(2)]),
        })
        listings = IdnesScraper(IDNES_CRITERIA, client).scrape()
        assert [(listing.id, listing.price) for listing in listings] == [
            (f"idnes:{_idnes_id(1)}", 18000), (f"idnes:{_idnes_id(2)}", 18500)]

    def test_stops_at_the_page_cap_and_says_so(self, monkeypatch, caplog):
        pages = {page: _idnes_page([_idnes_card(page + 1)], next_page=page + 1) for page in range(60)}
        client, _ = _serve_idnes_pages(monkeypatch, pages)
        listings = IdnesScraper(IDNES_CRITERIA, client).scrape()
        assert len(listings) == idnes.MAX_PAGES
        assert "pagination cap" in caplog.text

    def test_the_last_page_within_the_cap_says_nothing(self, monkeypatch, caplog):
        pages = {page: _idnes_page([_idnes_card(page + 1)], next_page=page + 1) for page in range(49)}
        pages[49] = _idnes_page([_idnes_card(50)])
        client, _ = _serve_idnes_pages(monkeypatch, pages)
        assert len(IdnesScraper(IDNES_CRITERIA, client).scrape()) == 50
        assert "pagination cap" not in caplog.text


def _idnes_advert_page(hrefs):
    large = "".join(
        f'<a class="carousel__item b-gallery__img-lg__item" data-fancybox="images" href="{href}">'
        f'<span><img data-lazy="{href}-thumb" src="https://img.example/no-image-gallery.png"></span></a>'
        for href in hrefs)
    small = "".join(f'<a class="b-gallery__imgs-sm__item" href="#"><img src="{href}-small.webp"></a>'
                    for href in hrefs)
    return (f'<html><body><div class="b-gallery carousel"><div class="carousel__list">{large}</div>'
            f'<div class="b-gallery__imgs-sm">{small}</div></div></body></html>')


class TestIdnesAdvertGallery:
    """The whole gallery from the full-size links of the advert page's
    gallery."""

    def test_lists_every_full_size_photo_in_the_pages_order(self):
        page = _idnes_advert_page(["https://img.example/a.jpg?gt=r", "https://img.example/b.jpg?gt=r"])
        assert idnes.gallery_from_advert_page(page) == (
            "https://img.example/a.jpg?gt=r", "https://img.example/b.jpg?gt=r")

    def test_lists_a_repeated_photo_once(self):
        page = _idnes_advert_page(["https://img.example/a.jpg?gt=r"] * 2)
        assert idnes.gallery_from_advert_page(page) == ("https://img.example/a.jpg?gt=r",)

    def test_a_gallery_without_links_has_no_photos(self):
        assert idnes.gallery_from_advert_page(_idnes_advert_page([])) == ()

    def test_leaves_out_links_outside_the_gallery(self):
        page = _idnes_advert_page(["https://img.example/a.jpg?gt=r"]).replace(
            "</body>", '<a data-fancybox="images" href="https://img.example/similar.jpg"></a></body>')
        assert idnes.gallery_from_advert_page(page) == ("https://img.example/a.jpg?gt=r",)

    def test_leaves_out_the_gallerys_videos_and_3d_tours(self):
        page = _idnes_advert_page(["https://img.example/a.jpg?gt=r"]).replace(
            '<div class="carousel__list">',
            '<div class="carousel__list">'
            '<a class="carousel__item b-gallery__img-lg__item" data-fancybox="images" data-fancybox-video=""'
            ' href="https://img.example/video/tour.mp4"></a>'
            '<a class="carousel__item" data-fancybox="images" data-fancybox-virtual="" data-type="iframe"'
            ' href="https://tour.example/show/?m=1"></a>')
        assert idnes.gallery_from_advert_page(page) == ("https://img.example/a.jpg?gt=r",)

    def test_a_page_without_a_gallery_is_broken(self):
        with pytest.raises(ScraperBrokenError):
            idnes.gallery_from_advert_page("<html><body>no gallery</body></html>")


class TestPortalCoverage:
    def test_every_portal_has_a_scraper(self):
        assert set(ALL_SCRAPERS) == set(get_args(Portal))


class TestEstateOfferTypeCoverage:
    """Every schema Literal estate/offer value has a portal mapping in every
    scraper - valid criteria can never KeyError at scrape time."""

    @pytest.mark.parametrize("estate_type", ["flat", "house", "land", "cottage"])
    @pytest.mark.parametrize("offer_type", ["rent", "sale"])
    def test_every_combination_builds_portal_params(self, estate_type, offer_type):
        criteria = Criteria(offer_type=offer_type, estate_type=estate_type,
                            place=PlaceRef("obvod", 78), max_price=25000)
        SrealityScraper(criteria, _refusing_client())._build_params(offset=0)
        BezrealitkyScraper(criteria, _refusing_client())._build_url()
        RemaxScraper(criteria, _refusing_client())._build_url()
        IdnesScraper(criteria, _refusing_client())._build_url()


class TestNarrowPlaceViews:
    """Each scraper narrows the resolved place to its own typed view at
    construction and holds no other portal's data afterwards."""

    def test_sreality_view_carries_only_sreality_fields(self):
        from rentczecher_engine.adapters.scrapers.location_resolver import resolve
        from rentczecher_engine.adapters.scrapers.sreality import SrealityPlace
        view = SrealityPlace.from_params(resolve(PlaceRef("obvod", 78)))
        assert view == SrealityPlace(district_id=5007, region_id=10)

    def test_bezrealitky_view_carries_only_its_region_id(self):
        from rentczecher_engine.adapters.scrapers.location_resolver import resolve
        from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyPlace
        view = BezrealitkyPlace.from_params(resolve(PlaceRef("okres", 3401)))
        assert view == BezrealitkyPlace(region_id="R441864")

    def test_remax_view_tells_the_single_region_truth(self):
        from rentczecher_engine.adapters.scrapers.location_resolver import resolve
        from rentczecher_engine.adapters.scrapers.remax import RemaxPlace
        assert RemaxPlace.from_params(resolve(PlaceRef("okres", 3401))) == RemaxPlace(
            region_id=43, district_ids=(3401,))
        kraj = RemaxPlace.from_params(resolve(PlaceRef("kraj", 43)))
        assert kraj.region_id == 43 and len(kraj.district_ids) == 7

    def test_idnes_view_names_the_search_area_by_its_ruian_code(self):
        from rentczecher_engine.adapters.scrapers.idnes import IdnesPlace
        from rentczecher_engine.adapters.scrapers.location_resolver import resolve
        assert IdnesPlace.from_params(resolve(PlaceRef("okres", 3401))) == IdnesPlace(locality="OKRES-3401")

    def test_scrapers_hold_no_full_place_params(self):
        from rentczecher_engine.adapters.scrapers.location_resolver import PlaceParams
        criteria = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78), max_price=25000)
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper, IdnesScraper):
            scraper = scraper_cls(criteria, _refusing_client())
            assert not any(isinstance(value, PlaceParams)
                           for value in vars(scraper).values()), scraper_cls.name


class TestPlaceResolutionFailure:
    """A scraper built for an unresolvable place raises PlaceNotFoundError
    instead of silently searching nowhere."""

    def test_unknown_place_raises_at_construction(self):
        criteria = Criteria(offer_type="rent", estate_type="flat",
                            place=PlaceRef("okres", 999999), max_price=25000)
        for scraper_cls in (SrealityScraper, BezrealitkyScraper, RemaxScraper, IdnesScraper):
            with pytest.raises(PlaceNotFoundError):
                scraper_cls(criteria, _refusing_client())
