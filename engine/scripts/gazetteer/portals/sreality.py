"""Sreality's search places, harvested from the facets its search page
embeds. The ids are the very ones its search form submits, so they are not
verified again."""

import json
import sqlite3

import httpx

from .portal import BROWSER_HEADERS, MatchedDistrict, MatchedRegion, PortalPlaces, add_unique

SEARCH_URL = "https://www.sreality.cz/hledani/prodej/byty"


class Sreality:
    name = "sreality"

    def fetch(self, client: httpx.Client) -> PortalPlaces[int, int]:
        response = client.get(SEARCH_URL, headers=BROWSER_HEADERS)
        response.raise_for_status()
        return parse_search_page(response.text)

    def verify(self, client: httpx.Client, regions: list[MatchedRegion[int]],
               districts: list[MatchedDistrict[int]]) -> None:
        """Nothing to verify: the ids come from the search page itself."""

    def store(self, conn: sqlite3.Connection, regions: list[MatchedRegion[int]],
              districts: list[MatchedDistrict[int]]) -> None:
        stmt = "INSERT INTO sreality_regions (kraj_code, region_id) VALUES (?, ?)"
        conn.executemany(stmt, [(region.kraj_code, region.ids) for region in regions])
        stmt = """
            INSERT INTO sreality_districts (okres_code, obvod_code, district_id)
            VALUES (?, ?, ?)
        """
        conn.executemany(stmt, [
            (district.okres_code, district.obvod_code, district.ids) for district in districts
        ])


def parse_search_page(html: str) -> PortalPlaces[int, int]:
    regions: dict[str, int] = {}
    for value in _facet_values(html, "locality_region_id"):
        add_unique(regions, value["name"], value["id"], "sreality")
    districts: dict[str, int] = {}
    for value in _facet_values(html, "locality_district_id"):
        add_unique(districts, value["name"], value["id"], "sreality")
    return PortalPlaces(regions=regions, districts=districts)


def _facet_values(html: str, id_name: str) -> list[dict]:
    """One facet's values from the page's hydration data. Next.js may stream
    a facet more than once, so every copy must agree."""
    marker = f'"idName":"{id_name}","values":'
    decoder = json.JSONDecoder()
    copies = []
    at = html.find(marker)
    while at != -1:
        values, _ = decoder.raw_decode(html, at + len(marker))
        copies.append(values)
        at = html.find(marker, at + len(marker))
    if not copies:
        raise SystemExit(f"sreality: no {id_name} facet in the search page, has its shape changed?")
    if any(copy != copies[0] for copy in copies[1:]):
        raise SystemExit(f"sreality: the {id_name} facet appears more than once, with differing values")
    return copies[0]
