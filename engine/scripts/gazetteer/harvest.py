"""Joins each portal's places to the official ones, then has the portal
verify and store them.

A portal region must be exactly one kraj, and a portal district exactly one
okres or Praha obvod, matched by name. Every official place must be mapped
by every portal: a profile may search any of them. A portal's extra names
that match nothing, such as the městské části some portals also list, are
reported and left out."""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import httpx

from rentczecher_engine.adapters.scrapers.location_resolver import normalize_name

from .portals.portal import MatchedDistrict, MatchedRegion, Portal

RegionIds = TypeVar("RegionIds")
DistrictIds = TypeVar("DistrictIds")


@dataclass(frozen=True, slots=True)
class OfficialPlace:
    code: int
    name: str


@dataclass(frozen=True, slots=True)
class OfficialPlaces:
    """The places a portal can search by, each under its normalized name."""

    kraje: dict[str, OfficialPlace]
    okresy: dict[str, OfficialPlace]
    obvody: dict[str, OfficialPlace]

    @classmethod
    def read(cls, conn: sqlite3.Connection) -> "OfficialPlaces":
        return cls(
            kraje=_by_normalized_name(conn, "SELECT code, name, name_norm FROM kraje"),
            okresy=_by_normalized_name(conn, "SELECT code, name, name_norm FROM okresy"),
            obvody=_by_normalized_name(conn, "SELECT code, name, name_norm FROM obvody"),
        )


def harvest_portals(path: Path, client: httpx.Client, portals: Sequence[Portal[Any, Any]]) -> None:
    """Fills every portal's tables in the gazetteer at path."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        official = OfficialPlaces.read(conn)
        for portal in portals:
            _harvest(conn, client, portal, official)
        conn.commit()
    finally:
        conn.close()


def _harvest(conn: sqlite3.Connection, client: httpx.Client, portal: Portal[Any, Any],
             official: OfficialPlaces) -> None:
    print(f"Harvesting {portal.name}")
    places = portal.fetch(client)
    regions = _match_regions(portal.name, places.regions, official)
    districts = _match_districts(portal.name, places.districts, official)
    portal.verify(client, regions, districts)
    portal.store(conn, regions, districts)
    print(f"  {len(regions)} kraje and {len(districts)} districts mapped")


def _match_regions(portal: str, regions: dict[str, RegionIds],
                   official: OfficialPlaces) -> list[MatchedRegion[RegionIds]]:
    matched: dict[int, MatchedRegion[RegionIds]] = {}
    ignored = []
    for name, ids in regions.items():
        kraj = official.kraje.get(normalize_name(name))
        if kraj is None:
            ignored.append(name)
            continue
        if kraj.code in matched:
            raise SystemExit(f"{portal}: {matched[kraj.code].name!r} and {name!r} both name kraj {kraj.name}")
        matched[kraj.code] = MatchedRegion(name=name, kraj_code=kraj.code, ids=ids)
    _require_all(portal, "kraje", official.kraje, set(matched))
    _report_ignored(portal, "regions", ignored)
    return list(matched.values())


def _match_districts(portal: str, districts: dict[str, DistrictIds],
                     official: OfficialPlaces) -> list[MatchedDistrict[DistrictIds]]:
    matched_okresy: dict[int, MatchedDistrict[DistrictIds]] = {}
    matched_obvody: dict[int, MatchedDistrict[DistrictIds]] = {}
    ignored = []
    for name, ids in districts.items():
        key = normalize_name(name)
        okres = official.okresy.get(key)
        obvod = official.obvody.get(key)
        if okres is not None and obvod is not None:
            raise SystemExit(f"{portal}: {name!r} names both okres {okres.name} and obvod {obvod.name}")
        if okres is not None:
            if okres.code in matched_okresy:
                raise SystemExit(f"{portal}: {matched_okresy[okres.code].name!r} and {name!r} "
                                 f"both name okres {okres.name}")
            matched_okresy[okres.code] = MatchedDistrict(name=name, okres_code=okres.code, obvod_code=None, ids=ids)
        elif obvod is not None:
            if obvod.code in matched_obvody:
                raise SystemExit(f"{portal}: {matched_obvody[obvod.code].name!r} and {name!r} "
                                 f"both name obvod {obvod.name}")
            matched_obvody[obvod.code] = MatchedDistrict(name=name, okres_code=None, obvod_code=obvod.code, ids=ids)
        else:
            ignored.append(name)
    _require_all(portal, "okresy", official.okresy, set(matched_okresy))
    _require_all(portal, "obvody", official.obvody, set(matched_obvody))
    _report_ignored(portal, "districts", ignored)
    return [*matched_okresy.values(), *matched_obvody.values()]


def _require_all(portal: str, kind: str, official: dict[str, OfficialPlace], mapped_codes: set[int]) -> None:
    missing = sorted(place.name for place in official.values() if place.code not in mapped_codes)
    if missing:
        raise SystemExit(f"{portal}: no mapping for {len(missing)} {kind}: {', '.join(missing)}")


def _report_ignored(portal: str, kind: str, ignored: list[str]) -> None:
    if ignored:
        print(f"  ignored {len(ignored)} {portal} {kind} that are no search place: {', '.join(sorted(ignored))}")


def _by_normalized_name(conn: sqlite3.Connection, stmt: str) -> dict[str, OfficialPlace]:
    places: dict[str, OfficialPlace] = {}
    for row in conn.execute(stmt):
        if row["name_norm"] in places:
            raise SystemExit(f"two official places share the name {row['name']!r}, a name join cannot tell them apart")
        places[row["name_norm"]] = OfficialPlace(code=row["code"], name=row["name"])
    return places
