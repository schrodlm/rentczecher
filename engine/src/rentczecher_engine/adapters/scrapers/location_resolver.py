import difflib
from dataclasses import dataclass
from functools import cache

from rentczecher_engine.adapters.geocoding.gazetteer import normalize_name, open_gazetteer
from rentczecher_engine.domain.errors import PlaceNotFoundError


def slugify(name: str) -> str:
    return normalize_name(name).replace(" ", "-")


@dataclass(frozen=True, slots=True)
class PlaceParams:
    slug: str
    name: str
    sreality_district_id: int | None
    sreality_region_id: int
    remax_regions: dict[int, tuple[int, ...]]
    bezrealitky_region_id: str


def resolve(place: str) -> PlaceParams:
    """Translate a place slug or free-text name into per-portal search
    parameters from the gazetteer. Raises PlaceNotFoundError with
    nearest-match suggestions when the place is unknown."""
    index = _index()
    key = slugify(place)
    params = index.get(key)
    if params is None:
        suggestions = tuple(difflib.get_close_matches(key, index, n=3, cutoff=0.6))
        raise PlaceNotFoundError(place, suggestions)
    return params


_REGIONS_STMT = """
    SELECT k.code AS kraj_code, k.name,
           s.region_id AS sreality_region_id,
           r.region_id AS remax_region_id,
           b.region_osm_id AS bezrealitky_region_id
    FROM kraje k
    JOIN sreality_regions s ON s.kraj_code = k.code
    JOIN remax_regions r ON r.kraj_code = k.code
    JOIN bezrealitky_regions b ON b.kraj_code = k.code
    ORDER BY k.name
"""

# An okres names its kraj. An obvod lies in Praha, whose kraj its obec names.
_DISTRICTS_STMT = """
    SELECT o.name, o.kraj_code,
           s.district_id AS sreality_district_id,
           r.region_id AS remax_region_id, r.district_id AS remax_district_id,
           b.region_osm_id AS bezrealitky_region_id
    FROM okresy o
    JOIN sreality_districts s ON s.okres_code = o.code
    JOIN remax_districts r ON r.okres_code = o.code
    JOIN bezrealitky_districts b ON b.okres_code = o.code
    UNION ALL
    SELECT ob.name, oc.kraj_code,
           s.district_id, r.region_id, r.district_id, b.region_osm_id
    FROM obvody ob
    JOIN obce oc ON oc.code = ob.obec_code
    JOIN sreality_districts s ON s.obvod_code = ob.code
    JOIN remax_districts r ON r.obvod_code = ob.code
    JOIN bezrealitky_districts b ON b.obvod_code = ob.code
    ORDER BY 1
"""


@cache
def _index() -> dict[str, PlaceParams]:
    """Every search place by its slug, read from the gazetteer's portal
    tables: the kraje, which search region-wide, and the districts, the
    okresy and Praha's obvody."""
    conn = open_gazetteer()
    try:
        regions = conn.execute(_REGIONS_STMT).fetchall()
        districts = conn.execute(_DISTRICTS_STMT).fetchall()
    finally:
        conn.close()

    sreality_region_by_kraj = {row["kraj_code"]: row["sreality_region_id"] for row in regions}
    index: dict[str, PlaceParams] = {}
    for row in districts:
        _add(index, PlaceParams(
            slug=slugify(row["name"]),
            name=row["name"],
            sreality_district_id=row["sreality_district_id"],
            sreality_region_id=sreality_region_by_kraj[row["kraj_code"]],
            remax_regions={row["remax_region_id"]: (row["remax_district_id"],)},
            bezrealitky_region_id=row["bezrealitky_region_id"],
        ))
    for row in regions:
        district_ids = tuple(
            district["remax_district_id"] for district in districts if district["kraj_code"] == row["kraj_code"]
        )
        _add(index, PlaceParams(
            slug=slugify(row["name"]),
            name=row["name"],
            sreality_district_id=None,
            sreality_region_id=row["sreality_region_id"],
            remax_regions={row["remax_region_id"]: district_ids},
            bezrealitky_region_id=row["bezrealitky_region_id"],
        ))
    return index


def _add(index: dict[str, PlaceParams], params: PlaceParams) -> None:
    """Names are unique across the searchable kinds, so a slug names one
    place. Two sharing one would make every lookup of it a guess."""
    if params.slug in index:
        raise RuntimeError(f"two search places share the slug {params.slug!r}")
    index[params.slug] = params
