import difflib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from rentczecher_engine.adapters.geocoding.gazetteer import normalize_name
from rentczecher_engine.domain.errors import PlaceNotFoundError

PLACES_PATH = Path(__file__).parent / "location_data" / "places.json"

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
    parameters from the shipped table. Raises PlaceNotFoundError with
    nearest-match suggestions when the place is unknown."""
    index = _index()
    key = slugify(place)
    params = index.get(key)
    if params is None:
        suggestions = tuple(difflib.get_close_matches(key, index, n=3, cutoff=0.6))
        raise PlaceNotFoundError(place, suggestions)
    return params


@cache
def _index() -> dict[str, PlaceParams]:
    places = json.loads(PLACES_PATH.read_text(encoding="utf-8"))
    sreality_region_by_slug = {r["slug"]: r["sreality_region_id"] for r in places["regions"]}

    index: dict[str, PlaceParams] = {}
    for district in places["districts"]:
        index[district["slug"]] = PlaceParams(
            slug=district["slug"],
            name=district["name"],
            sreality_district_id=district["sreality_district_id"],
            sreality_region_id=sreality_region_by_slug[district["region_slug"]],
            remax_regions={district["remax_region_id"]: (district["remax_district_id"],)},
            bezrealitky_region_id=district["bezrealitky_region_id"],
        )

    for region in places["regions"]:
        children = [d for d in places["districts"] if d["region_slug"] == region["slug"]]
        index[region["slug"]] = PlaceParams(
            slug=region["slug"],
            name=region["name"],
            sreality_district_id=None,
            sreality_region_id=region["sreality_region_id"],
            remax_regions={region["remax_region_id"]: tuple(
                d["remax_district_id"] for d in children
            )},
            bezrealitky_region_id=region["bezrealitky_region_id"],
        )

    return index
