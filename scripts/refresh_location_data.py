#!/usr/bin/env python3
"""Regenerate the shipped location table (places.json) from the portals.

Maintainer tool - run rarely, by hand, when a portal renumbers its taxonomy:

    uv run python scripts/refresh_location_data.py

Harvests each portal's own location taxonomy (Sreality search-page facets,
RE/MAX search-form checkboxes, Bezrealitky's czechRegions GraphQL tree),
joins them by normalized district name, live-verifies every Bezrealitky id
against the portal's server-rendered search page, and only then writes
places.json. Any unmatched name or failed verification aborts without
writing.

Places Bezrealitky's tree lacks come from overrides.json. Their Praha
search ids are not OSM relations and not derivable from any API - the
portal's own frontend ships them as a hardcoded table (Praha 1-22) in its
JS bundle, so the overrides mirror the rows this table needs (Praha 1-10,
the other portals' granularity ceiling). Overridden ids still pass the
live verification.

To re-derive Bezrealitky's hardcoded ids (if they renumber): fetch any
bezrealitky.cz page, take the /_next/static/chunks/pages/_app-*.js URL
from its HTML, and grep the chunk for name:"..."/osmId:"R..." pairs.

The name join is collision-free only at district granularity; expanding
below it (village names repeat across the country) needs a composite
region-scoped key and a cheaper verification strategy than one request
per place.
"""

import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import httpx

from rentczecher.adapters.scrapers.location_resolver import normalize_name, slugify

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCATION_DATA_DIR = REPO_ROOT / "src" / "rentczecher" / "adapters" / "scrapers" / "location_data"
PLACES_PATH = LOCATION_DATA_DIR / "places.json"
OVERRIDES_PATH = LOCATION_DATA_DIR / "overrides.json"

SREALITY_SEARCH_URL = "https://www.sreality.cz/hledani/prodej/byty"
REMAX_FORM_URL = "https://www.remax-czech.cz/reality/vyhledavani/?hledani=1"
BEZREALITKY_GRAPHQL_URL = "https://api.bezrealitky.cz/graphql/"
BEZREALITKY_SEARCH_URL = "https://www.bezrealitky.cz/vyhledat"

# Sreality serves browser UAs only; the others tolerate anything.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}

REQUEST_SPACING_S = 1.0

CZECH_REGIONS_QUERY = """{
  czechRegions(locale: CS) {
    id name osmId
    children { id name osmId }
  }
}"""


def parse_sreality_facets(html: str) -> tuple[list[dict], list[dict]]:
    """Extract the region and district facet arrays embedded in the
    server-rendered search page."""
    def facet_values(id_name: str) -> list[dict]:
        # Next.js streams hydration data in chunks that may repeat a facet;
        # harvest only when every copy agrees rather than trusting the first.
        marker = f'"idName":"{id_name}","values":'
        decoder = json.JSONDecoder()
        copies = []
        at = html.find(marker)
        while at != -1:
            values, _ = decoder.raw_decode(html, at + len(marker))
            copies.append(values)
            at = html.find(marker, at + len(marker))
        if not copies:
            raise SystemExit(f"sreality: facet {id_name} not found in the search page - page shape changed?")
        if any(copy != copies[0] for copy in copies[1:]):
            raise SystemExit(f"sreality: facet {id_name} appears multiple times with differing content")
        return copies[0]

    regions = [{"id": v["id"], "name": v["name"]} for v in facet_values("locality_region_id")]
    districts = [
        {"id": v["id"], "name": v["name"], "region_id": v["regionId"]}
        for v in facet_values("locality_district_id")
    ]
    return regions, districts


def parse_remax_form(html: str) -> list[dict]:
    """Extract the two-level region checkbox tree from the search form:
    <h4> kraj headings followed by regions[R][D] checkboxes with labels.

    RE/MAX numbers regions and districts from one global sequence, so a
    district id can equal an unrelated kraj's region id (Praha 1 is
    regions[19][19] while 19 is also the Praha region itself); only the
    (region_id, district_id) pair identifies a place, never district_id
    alone."""
    checkbox_re = re.compile(
        r'name="regions\[(\d+)\]\[(\d+)\]".*?<label[^>]*>([^<]+)</label>', re.DOTALL,
    )
    rows = []
    chunks = re.split(r"<h4>([^<]+)</h4>", html)
    for heading, chunk in zip(chunks[1::2], chunks[2::2]):
        for region_id, district_id, label in checkbox_re.findall(chunk):
            rows.append({
                "region_name": heading.strip(),
                "region_id": int(region_id),
                "district_id": int(district_id),
                "district_name": label.strip(),
            })
    if not rows:
        raise SystemExit("remax: no region checkboxes found in the search form - page shape changed?")
    return rows


def _put_unique(index: dict, key: str, value, source: str) -> None:
    """Two different places collapsing onto one join key would let the join
    silently pick one of them; refuse instead."""
    if key in index and index[key] != value:
        raise SystemExit(f"{source}: name collision on {key!r} - refusing to guess between "
                         f"{index[key]!r} and {value!r}")
    index[key] = value


def parse_bezrealitky_regions(payload: dict) -> tuple[dict[str, int], dict[str, int]]:
    """Map normalized kraj and okres names to osmIds from czechRegions."""
    regions = payload.get("data", {}).get("czechRegions")
    if not regions:
        raise SystemExit(f"bezrealitky: czechRegions returned no data: {json.dumps(payload)[:200]}")
    kraje: dict[str, int] = {}
    okresy: dict[str, int] = {}
    for region in regions:
        _put_unique(kraje, normalize_name(region["name"]), region["osmId"], "bezrealitky kraje")
        for child in region.get("children") or []:
            _put_unique(okresy, normalize_name(child["name"]), child["osmId"], "bezrealitky okresy")
    return kraje, okresy


def verify_bezrealitky_id(client: httpx.Client, osm_id: str, expected_name: str) -> bool:
    """The search page server-renders the resolved place name into its <h1>
    ('Všechny typy nabídek • okres Domažlice'); an id the portal does not
    recognize renders no such segment."""
    time.sleep(REQUEST_SPACING_S)
    resp = client.get(BEZREALITKY_SEARCH_URL, params={"regionOsmIds": osm_id})
    resp.raise_for_status()
    expected = normalize_name(expected_name)
    for heading_html in re.findall(r"<h1[^>]*>(.*?)</h1>", resp.text, re.DOTALL):
        heading = re.sub(r"<[^>]+>", "", heading_html)
        if expected in (normalize_name(part) for part in heading.split("•")):
            return True
    return False


def load_overrides() -> dict:
    if OVERRIDES_PATH.exists():
        return json.loads(OVERRIDES_PATH.read_text())
    return {"regions": {}, "districts": {}}


def _apply_overrides(row: dict, entry: dict) -> None:
    """An override shadowing a value the portals now supply themselves means
    the portal may have corrected the quirk the override works around; say so
    instead of hiding fresh data forever."""
    for field, value in entry.items():
        if row.get(field) is not None and row[field] != value:
            print(f"NOTICE: {row['name']}: override {field}={value!r} shadows harvested "
                  f"{row[field]!r} - re-evaluate whether the override is still needed "
                  f"(see the why entry in overrides.json)")
        row[field] = value


def build_places(client: httpx.Client) -> dict:
    print("Fetching sreality facets...")
    resp = client.get(SREALITY_SEARCH_URL, headers=BROWSER_HEADERS)
    resp.raise_for_status()
    sre_regions, sre_districts = parse_sreality_facets(resp.text)
    print(f"  {len(sre_regions)} regions, {len(sre_districts)} districts")

    time.sleep(REQUEST_SPACING_S)
    print("Fetching remax form...")
    resp = client.get(REMAX_FORM_URL, headers=BROWSER_HEADERS)
    resp.raise_for_status()
    remax_rows = parse_remax_form(resp.text)
    print(f"  {len(remax_rows)} district checkboxes")

    time.sleep(REQUEST_SPACING_S)
    print("Fetching bezrealitky czechRegions...")
    resp = client.post(BEZREALITKY_GRAPHQL_URL, json={"query": CZECH_REGIONS_QUERY},
                       headers=BROWSER_HEADERS)
    resp.raise_for_status()
    bez_kraje, bez_okresy = parse_bezrealitky_regions(resp.json())
    print(f"  {len(bez_kraje)} kraje, {len(bez_okresy)} okresy")

    overrides = load_overrides()
    remax_regions: dict = {}
    remax_districts: dict = {}
    for remax_row in remax_rows:
        _put_unique(remax_regions, normalize_name(remax_row["region_name"]),
                    remax_row["region_id"], "remax regions")
        _put_unique(remax_districts, normalize_name(remax_row["district_name"]),
                    remax_row, "remax districts")

    unmatched = []

    regions = []
    for sre_region in sorted(sre_regions, key=lambda r: r["name"]):
        key = normalize_name(sre_region["name"])
        slug = slugify(sre_region["name"])
        row = {
            "name": sre_region["name"],
            "slug": slug,
            "sreality_region_id": sre_region["id"],
            "remax_region_id": remax_regions.get(key),
            "bezrealitky_region_id": f"R{bez_kraje[key]}" if key in bez_kraje else None,
        }
        _apply_overrides(row, overrides.get("regions", {}).get(slug, {}))
        if row["remax_region_id"] is None:
            unmatched.append(f"region {sre_region['name']!r}: no remax match - fix normalization or add an override")
        if row["bezrealitky_region_id"] is None:
            unmatched.append(f"region {sre_region['name']!r}: no bezrealitky match - fix normalization or add an override")
        regions.append(row)

    region_slug_by_id = {r["sreality_region_id"]: r["slug"] for r in regions}

    districts = []
    for sre_district in sorted(sre_districts, key=lambda d: d["name"]):
        key = normalize_name(sre_district["name"])
        slug = slugify(sre_district["name"])
        remax_row = remax_districts.get(key)
        row = {
            "name": sre_district["name"],
            "slug": slug,
            "region_slug": region_slug_by_id.get(sre_district["region_id"]),
            "sreality_district_id": sre_district["id"],
            "remax_region_id": remax_row["region_id"] if remax_row else None,
            "remax_district_id": remax_row["district_id"] if remax_row else None,
            "bezrealitky_region_id": f"R{bez_okresy[key]}" if key in bez_okresy else None,
        }
        _apply_overrides(row, overrides.get("districts", {}).get(slug, {}))
        if row["region_slug"] is None:
            unmatched.append(f"district {sre_district['name']!r}: sreality region id "
                             f"{sre_district['region_id']} is not in the region facet")
        if row["remax_region_id"] is None or row["remax_district_id"] is None:
            unmatched.append(f"district {sre_district['name']!r}: no remax match - fix normalization or add an override")
        if row["bezrealitky_region_id"] is None:
            unmatched.append(f"district {sre_district['name']!r}: not in czechRegions - add an override")
        districts.append(row)

    if unmatched:
        for line in unmatched:
            print(f"UNMATCHED: {line}", file=sys.stderr)
        raise SystemExit("aborting: cross-portal name join failed - fix normalization or add overrides")

    to_verify = [(r["bezrealitky_region_id"], r["name"]) for r in regions + districts]
    print(f"Verifying {len(to_verify)} bezrealitky ids against live search pages...")
    failures = []
    for osm_id, name in to_verify:
        if verify_bezrealitky_id(client, osm_id, name):
            print(f"  ok: {name} ({osm_id})")
        else:
            failures.append(f"{name} ({osm_id})")
            print(f"  FAILED: {name} ({osm_id})", file=sys.stderr)
    if failures:
        raise SystemExit(f"aborting: {len(failures)} bezrealitky ids failed live verification - add overrides")

    return {"generated_at": date.today().isoformat(), "regions": regions, "districts": districts}


def main() -> None:
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            places = build_places(client)
    except httpx.HTTPError as error:
        raise SystemExit(f"aborting: network error while harvesting - {error}")
    LOCATION_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLACES_PATH.write_text(json.dumps(places, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(places['regions'])} regions and {len(places['districts'])} districts to {PLACES_PATH}")


if __name__ == "__main__":
    main()
