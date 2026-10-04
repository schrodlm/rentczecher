"""Sampled live proof that the gazetteer's portal ids still work on the real
portals, the check that catches a portal renumbering its places between
gazetteer builds.

Run: uv run pytest -m live tests/live/test_search_places.py -v
"""

import time

import httpx
import pytest

from rentczecher_engine.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher_engine.domain.location import PlaceRef
from scripts.gazetteer.portals.bezrealitky import heading_names
from scripts.gazetteer.portals.portal import BROWSER_HEADERS, REQUEST_SPACING_S

SAMPLE = [
    PlaceRef("obvod", 19),
    PlaceRef("obvod", 78),
    PlaceRef("okres", 3401),
    PlaceRef("okres", 3805),
]


@pytest.fixture(scope="module")
def client():
    with httpx.Client(timeout=30, follow_redirects=True, headers=BROWSER_HEADERS) as c:
        yield c


@pytest.fixture(scope="module")
def sample() -> list[PlaceParams]:
    return [resolve(place) for place in SAMPLE]


def test_sreality_district_ids_return_listings(sample, client):
    """A district id Sreality no longer knows returns nothing or everything."""
    for place in sample:
        time.sleep(REQUEST_SPACING_S)
        response = client.get("https://www.sreality.cz/api/v1/estates/search",
                              params={"locality_district_id": place.sreality_district_id,
                                      "per_page": 1, "lang": "cs"},
                              headers={"Accept": "application/json"})
        assert response.status_code == 200, place.name
        assert response.json()["pagination"]["total"] > 0, place.name


def test_bezrealitky_ids_are_named_by_the_search(sample, client):
    """The search page's heading names the place an id stands for."""
    for place in sample:
        time.sleep(REQUEST_SPACING_S)
        response = client.get("https://www.bezrealitky.cz/vyhledat",
                              params={"regionOsmIds": place.bezrealitky_region_id})
        assert response.status_code == 200, place.name
        assert heading_names(response.text, place.name), place.name


def test_remax_region_and_district_pairs_are_accepted(sample, client):
    """RE/MAX's search form still accepts each region and district pair."""
    for place in sample:
        (region_id, district_ids), = place.remax_regions.items()
        time.sleep(REQUEST_SPACING_S)
        response = client.get("https://www.remax-czech.cz/reality/vyhledavani/",
                              params={"hledani": 1, f"regions[{region_id}][{district_ids[0]}]": "on"})
        assert response.status_code == 200, place.name
