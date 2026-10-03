"""Bezrealitky's search places, from two sources.

Its GraphQL API lists the kraje and their okresy. Praha is the exception:
the API's id for it is one the search does not recognize, and under it the
API lists části obce, not obvody. The search's own Praha ids exist only as a
table hardcoded in the site's JavaScript bundle, so they are read from
there. The API's ids are trusted like a search form's, but the bundle is the
site's internal code, so each id read from it is verified against the live
search before it is stored."""

import re
import sqlite3
import time

import httpx

from rentczecher_engine.adapters.scrapers.location_resolver import normalize_name

from .portal import (
    BROWSER_HEADERS,
    REQUEST_SPACING_S,
    MatchedDistrict,
    MatchedRegion,
    PortalPlaces,
    add_unique,
)

GRAPHQL_URL = "https://api.bezrealitky.cz/graphql/"
HOME_URL = "https://www.bezrealitky.cz/"
SEARCH_URL = "https://www.bezrealitky.cz/vyhledat"

REGIONS_QUERY = """{
  czechRegions(locale: CS) {
    name osmId
    children { name osmId }
  }
}"""

_APP_BUNDLE = re.compile(r'(/_next/static/chunks/pages/_app-[^"]+\.js)')
_PRAHA_IDS = re.compile(r'name:"(Praha(?: \d+)?)",osmId:"(R\d+)"')
_HEADING = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")

_PRAHA = normalize_name("Praha")


class Bezrealitky:
    name = "bezrealitky"

    def __init__(self) -> None:
        self._bundle_ids: set[str] = set()

    def fetch(self, client: httpx.Client) -> PortalPlaces[str, str]:
        regions, districts = _api_places(client)
        bundle_regions, bundle_districts = _bundle_places(client)
        self._bundle_ids = set(bundle_regions.values()) | set(bundle_districts.values())
        # The bundle's Praha id is the one the search recognizes, so it
        # replaces the API's.
        regions = {name: ids for name, ids in regions.items() if normalize_name(name) != _PRAHA}
        for name, ids in bundle_regions.items():
            add_unique(regions, name, ids, self.name)
        for name, ids in bundle_districts.items():
            add_unique(districts, name, ids, self.name)
        return PortalPlaces(regions=regions, districts=districts)

    def verify(self, client: httpx.Client, regions: list[MatchedRegion[str]],
               districts: list[MatchedDistrict[str]]) -> None:
        """Checks the matched ids that came from the bundle. The API's ids
        are what the site itself serves, so they are trusted."""
        from_bundle = {region.name: region.ids for region in regions if region.ids in self._bundle_ids}
        from_bundle.update(
            {district.name: district.ids for district in districts if district.ids in self._bundle_ids})
        _verify(client, from_bundle)

    def store(self, conn: sqlite3.Connection, regions: list[MatchedRegion[str]],
              districts: list[MatchedDistrict[str]]) -> None:
        stmt = "INSERT INTO bezrealitky_regions (kraj_code, region_osm_id) VALUES (?, ?)"
        conn.executemany(stmt, [(region.kraj_code, region.ids) for region in regions])
        stmt = """
            INSERT INTO bezrealitky_districts (okres_code, obvod_code, region_osm_id)
            VALUES (?, ?, ?)
        """
        conn.executemany(stmt, [
            (district.okres_code, district.obvod_code, district.ids) for district in districts
        ])


def _api_places(client: httpx.Client) -> tuple[dict[str, str], dict[str, str]]:
    response = client.post(GRAPHQL_URL, json={"query": REGIONS_QUERY}, headers=BROWSER_HEADERS)
    response.raise_for_status()
    return parse_regions(response.json())


def parse_regions(payload: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Kraje and okresy from the czechRegions answer. Praha's children are
    its části obce, which the search does not offer, so they are skipped."""
    kraje = (payload.get("data") or {}).get("czechRegions")
    if not kraje:
        raise SystemExit("bezrealitky: czechRegions returned no regions, has the API changed?")
    regions: dict[str, str] = {}
    districts: dict[str, str] = {}
    for kraj in kraje:
        add_unique(regions, kraj["name"], f"R{kraj['osmId']}", "bezrealitky")
        if normalize_name(kraj["name"]) == _PRAHA:
            continue
        for okres in kraj["children"] or []:
            add_unique(districts, okres["name"], f"R{okres['osmId']}", "bezrealitky")
    return regions, districts


def _bundle_places(client: httpx.Client) -> tuple[dict[str, str], dict[str, str]]:
    time.sleep(REQUEST_SPACING_S)
    home = client.get(HOME_URL, headers=BROWSER_HEADERS)
    home.raise_for_status()
    bundle_path = _APP_BUNDLE.search(home.text)
    if bundle_path is None:
        raise SystemExit("bezrealitky: no _app bundle linked from the home page, has the site changed?")
    time.sleep(REQUEST_SPACING_S)
    bundle = client.get(HOME_URL.rstrip("/") + bundle_path.group(1), headers=BROWSER_HEADERS)
    bundle.raise_for_status()
    return parse_bundle(bundle.text)


def parse_bundle(javascript: str) -> tuple[dict[str, str], dict[str, str]]:
    """Praha itself and its numbered districts from the bundle's table of
    name and osmId pairs."""
    regions: dict[str, str] = {}
    districts: dict[str, str] = {}
    for name, osm_id in _PRAHA_IDS.findall(javascript):
        add_unique(regions if name == "Praha" else districts, name, osm_id, "bezrealitky")
    if not regions or not districts:
        raise SystemExit("bezrealitky: no Praha ids in the bundle, has its table changed?")
    return regions, districts


def _verify(client: httpx.Client, ids_by_name: dict[str, str]) -> None:
    """Asks the live search for each id. Its page names the place in the
    heading ('Všechny typy nabídek • okres Domažlice'), and an id it does not
    recognize names none."""
    print(f"  verifying {len(ids_by_name)} bezrealitky ids from its bundle against the live search")
    failed = []
    for name, osm_id in ids_by_name.items():
        time.sleep(REQUEST_SPACING_S)
        response = client.get(SEARCH_URL, params={"regionOsmIds": osm_id}, headers=BROWSER_HEADERS)
        response.raise_for_status()
        if not heading_names(response.text, name):
            failed.append(f"{name} ({osm_id})")
    if failed:
        raise SystemExit(f"bezrealitky: {len(failed)} ids are not recognized by the search: {', '.join(failed)}")


def heading_names(html: str, name: str) -> bool:
    """Does the search page's heading name this place?"""
    expected = normalize_name(name)
    for heading in _HEADING.findall(html):
        parts = _TAG.sub("", heading).split("•")
        if expected in (normalize_name(part) for part in parts):
            return True
    return False
