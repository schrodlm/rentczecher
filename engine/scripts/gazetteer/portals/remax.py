"""RE/MAX's search places, harvested from the region tree of its search form.
The ids are the very ones the form submits, so they are not verified again."""

import re
import sqlite3
from dataclasses import dataclass

import httpx

from .portal import BROWSER_HEADERS, PRAHA_KRAJ, MatchedDistrict, MatchedRegion, PortalPlaces, add_unique

FORM_URL = "https://www.remax-czech.cz/reality/vyhledavani/?hledani=1"

# The form lists each kraj as an <h4> heading followed by one checkbox per
# district, named regions[region id][district id] and labelled with its name.
_HEADING = re.compile(r"<h4>([^<]+)</h4>")
_CHECKBOX = re.compile(r'name="regions\[(\d+)\]\[(\d+)\]".*?<label[^>]*>([^<]+)</label>', re.DOTALL)


@dataclass(frozen=True, slots=True)
class RemaxDistrict:
    """RE/MAX numbers regions and districts from one sequence, so a district
    id alone can equal an unrelated region's id. Only the pair identifies a
    district."""

    region_id: int
    district_id: int


class Remax:
    name = "remax"

    def fetch(self, client: httpx.Client) -> PortalPlaces[int, RemaxDistrict]:
        response = client.get(FORM_URL, headers=BROWSER_HEADERS)
        response.raise_for_status()
        return parse_search_form(response.text)

    def verify(self, client: httpx.Client, regions: list[MatchedRegion[int]],
               districts: list[MatchedDistrict[RemaxDistrict]]) -> None:
        """Nothing to verify: the ids come from the search form itself."""

    def store(self, conn: sqlite3.Connection, regions: list[MatchedRegion[int]],
              districts: list[MatchedDistrict[RemaxDistrict]]) -> None:
        stmt = "INSERT INTO remax_regions (kraj_code, region_id) VALUES (?, ?)"
        conn.executemany(stmt, [(region.kraj_code, region.ids) for region in regions])
        stmt = """
            INSERT INTO remax_districts (okres_code, obvod_code, region_id, district_id)
            VALUES (?, ?, ?, ?)
        """
        conn.executemany(stmt, [
            (district.okres_code, district.obvod_code, district.ids.region_id, district.ids.district_id)
            for district in districts
        ])


def _official_kraj_name(heading: str) -> str:
    """The form drops the word kraj ('Plzeňský') and calls the capital
    'Praha'. RÚIAN names them 'Plzeňský kraj' and 'Hlavní město Praha'."""
    if heading == "Praha":
        return PRAHA_KRAJ
    if heading == "Vysočina":
        return "Kraj Vysočina"
    return f"{heading} kraj"


def parse_search_form(html: str) -> PortalPlaces[int, RemaxDistrict]:
    regions: dict[str, int] = {}
    districts: dict[str, RemaxDistrict] = {}
    chunks = _HEADING.split(html)
    for heading, chunk in zip(chunks[1::2], chunks[2::2]):
        for region_id, district_id, label in _CHECKBOX.findall(chunk):
            add_unique(regions, _official_kraj_name(heading.strip()), int(region_id), "remax")
            add_unique(districts, label.strip(), RemaxDistrict(int(region_id), int(district_id)), "remax")
    if not districts:
        raise SystemExit("remax: no region checkboxes in the search form, has its shape changed?")
    return PortalPlaces(regions=regions, districts=districts)
