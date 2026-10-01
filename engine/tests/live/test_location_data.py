"""Sampled live checks that the shipped place table's ids still work on the
real portals.

Run: python3 -m pytest -m live tests/live/test_location_data.py -v
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent.parent

_spec = importlib.util.spec_from_file_location(
    "refresh_location_data", ENGINE / "scripts" / "refresh_location_data.py")
harvest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harvest)

PLACES_PATH = ENGINE / "src" / "rentczecher_engine" / "adapters" / "scrapers" / "location_data" / "places.json"


@pytest.fixture(scope="module")
def places():
    return json.loads(PLACES_PATH.read_text())


class TestShippedIdsLive:
    """Sampled proof that shipped ids still work on the real portals - the
    test that catches a portal renumbering its taxonomy (like RE/MAX retiring
    district 3402)."""

    @pytest.fixture(scope="class")
    def client(self):
        import httpx as _httpx
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
        with _httpx.Client(timeout=30, follow_redirects=True, headers=headers) as c:
            yield c

    def _sample(self, places):
        by_slug = {d["slug"]: d for d in places["districts"]}
        return [by_slug["praha-1"], by_slug["praha-7"], by_slug["domazlice"], by_slug["olomouc"]]

    def test_sreality_ids_filter_searches(self, places, client):
        import time
        for district in self._sample(places):
            time.sleep(1)
            resp = client.get("https://www.sreality.cz/api/v1/estates/search",
                              params={"locality_district_id": district["sreality_district_id"],
                                      "per_page": 1, "lang": "cs"},
                              headers={"Accept": "application/json"})
            assert resp.status_code == 200, district["slug"]
            assert resp.json()["pagination"]["total"] > 0, district["slug"]

    def test_bezrealitky_ids_resolve_to_their_names(self, places, client):
        import time
        for district in self._sample(places):
            time.sleep(1)
            resp = client.get("https://www.bezrealitky.cz/vyhledat",
                              params={"regionOsmIds": district["bezrealitky_region_id"]})
            assert resp.status_code == 200, district["slug"]
            heading = re.search(r"<h1[^>]*>(.*?)</h1>", resp.text, re.DOTALL)
            assert heading is not None, district["slug"]
            assert harvest.normalize_name(district["name"]) in [
                harvest.normalize_name(part)
                for part in re.sub(r"<[^>]+>", "", heading.group(1)).split("•")
            ], district["slug"]

    def test_remax_ids_are_accepted_by_the_search_form(self, places, client):
        import time
        for district in self._sample(places):
            time.sleep(1)
            resp = client.get(
                "https://www.remax-czech.cz/reality/vyhledavani/",
                params={"hledani": 1,
                        f"regions[{district['remax_region_id']}][{district['remax_district_id']}]": "on"},
            )
            assert resp.status_code == 200, district["slug"]
