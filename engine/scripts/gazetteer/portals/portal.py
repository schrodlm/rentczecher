"""The contract every portal module fulfils, and the places it reports.

A portal names the places it can search by in its own words, with its own
ids. The harvest joins those names to the official places and hands the
matches back to the portal to verify and store, so everything a portal
knows stays in its own module."""

import sqlite3
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

import httpx

RegionIds = TypeVar("RegionIds")
DistrictIds = TypeVar("DistrictIds")

# Sreality serves browser user agents only, the others accept anything.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}

# Pause between requests to one portal, to stay a polite visitor.
REQUEST_SPACING_S = 1.0


@dataclass(frozen=True, slots=True)
class PortalPlaces(Generic[RegionIds, DistrictIds]):
    """A portal's own regions (kraje) and districts (okresy, and Praha's
    obvody), each under the portal's name for it."""

    regions: dict[str, RegionIds]
    districts: dict[str, DistrictIds]


@dataclass(frozen=True, slots=True)
class MatchedRegion(Generic[RegionIds]):
    """name is the portal's own name for the kraj."""

    name: str
    kraj_code: int
    ids: RegionIds


@dataclass(frozen=True, slots=True)
class MatchedDistrict(Generic[DistrictIds]):
    """name is the portal's own name for the place. Exactly one of
    okres_code and obvod_code is set."""

    name: str
    okres_code: int | None
    obvod_code: int | None
    ids: DistrictIds


class Portal(Protocol[RegionIds, DistrictIds]):
    name: str

    def fetch(self, client: httpx.Client) -> PortalPlaces[RegionIds, DistrictIds]:
        """The portal's places, scraped from its own site."""
        ...

    def verify(self, client: httpx.Client, regions: list[MatchedRegion[RegionIds]],
               districts: list[MatchedDistrict[DistrictIds]]) -> None:
        """Checks against the live portal any matched id that does not come
        from a source the portal itself relies on, and raises SystemExit
        when one is not recognized."""
        ...

    def store(self, conn: sqlite3.Connection, regions: list[MatchedRegion[RegionIds]],
              districts: list[MatchedDistrict[DistrictIds]]) -> None:
        """Writes the matched places into the portal's own tables."""
        ...


def add_unique(places: dict, name: str, ids: object, portal: str) -> None:
    """A name a portal repeats with the same ids is harmless. With different
    ids, picking one would be a guess, so the harvest refuses."""
    if name in places and places[name] != ids:
        raise SystemExit(f"{portal}: {name!r} appears with two ids, {places[name]!r} and {ids!r}")
    places[name] = ids
