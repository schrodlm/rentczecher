from dataclasses import dataclass
from functools import cache

from rentczecher_engine.adapters.geocoding.gazetteer import open_gazetteer
from rentczecher_engine.domain.errors import PlaceNotFoundError
from rentczecher_engine.domain.location import PlaceRef


@dataclass(frozen=True, slots=True)
class PlaceParams:
    name: str
    sreality_district_id: int | None
    sreality_region_id: int
    remax_regions: dict[int, tuple[int, ...]]
    bezrealitky_region_id: str


def resolve(place: PlaceRef) -> PlaceParams:
    """Translate a search place into per-portal search parameters from the
    gazetteer. Raises PlaceNotFoundError for a place no portal searches."""
    params = _index().get(place)
    if params is None:
        raise PlaceNotFoundError(f"{place.kind} {place.code}")
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
"""

# An okres names its kraj. An obvod lies in Praha, whose kraj its obec names.
_DISTRICTS_STMT = """
    SELECT 'okres' AS kind, o.code, o.name, o.kraj_code,
           s.district_id AS sreality_district_id,
           r.region_id AS remax_region_id, r.district_id AS remax_district_id,
           b.region_osm_id AS bezrealitky_region_id
    FROM okresy o
    JOIN sreality_districts s ON s.okres_code = o.code
    JOIN remax_districts r ON r.okres_code = o.code
    JOIN bezrealitky_districts b ON b.okres_code = o.code
    UNION ALL
    SELECT 'obvod', ob.code, ob.name, oc.kraj_code,
           s.district_id, r.region_id, r.district_id, b.region_osm_id
    FROM obvody ob
    JOIN obce oc ON oc.code = ob.obec_code
    JOIN sreality_districts s ON s.obvod_code = ob.code
    JOIN remax_districts r ON r.obvod_code = ob.code
    JOIN bezrealitky_districts b ON b.obvod_code = ob.code
"""


@cache
def _index() -> dict[PlaceRef, PlaceParams]:
    """Every search place by its kind and code, read from the gazetteer's
    portal tables: the kraje, which search region-wide, and the districts,
    the okresy and Praha's obvody."""
    conn = open_gazetteer()
    try:
        regions = conn.execute(_REGIONS_STMT).fetchall()
        districts = conn.execute(_DISTRICTS_STMT).fetchall()
    finally:
        conn.close()

    sreality_region_by_kraj = {row["kraj_code"]: row["sreality_region_id"] for row in regions}
    index: dict[PlaceRef, PlaceParams] = {}
    for row in districts:
        index[PlaceRef(kind=row["kind"], code=row["code"])] = PlaceParams(
            name=row["name"],
            sreality_district_id=row["sreality_district_id"],
            sreality_region_id=sreality_region_by_kraj[row["kraj_code"]],
            remax_regions={row["remax_region_id"]: (row["remax_district_id"],)},
            bezrealitky_region_id=row["bezrealitky_region_id"],
        )
    for row in regions:
        district_ids = tuple(
            district["remax_district_id"] for district in districts if district["kraj_code"] == row["kraj_code"]
        )
        index[PlaceRef(kind="kraj", code=row["kraj_code"])] = PlaceParams(
            name=row["name"],
            sreality_district_id=None,
            sreality_region_id=row["sreality_region_id"],
            remax_regions={row["remax_region_id"]: district_ids},
            bezrealitky_region_id=row["bezrealitky_region_id"],
        )
    return index
