"""Offline geocoding: portal location text to coordinates, no network.

Lookups run against the shipped gazetteer.sqlite (built by the location
refresh script from the state address registry).
"""

import re
import sqlite3
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from rentczecher.adapters.scrapers.location_resolver import normalize_name

# Portal location strings put a house number after the street name
# ("Škarmanská 369 / 369"); the gazetteer knows streets, not buildings.
_HOUSE_NUMBER = re.compile(r"\b\d+[a-z]?(\s*/\s*\d+[a-z]?)?\b")

_TIERS_MOST_SPECIFIC_FIRST = ("street", "municipality_part", "city_district", "municipality")


@dataclass(frozen=True, slots=True)
class ResolvedPlace:
    name: str
    muni_name: str | None  # a resolved district has no municipality
    okres_name: str | None
    tier: str
    lat: float
    lon: float


def candidate_names(location: str) -> list[str]:
    """Normalized lookup candidates from one portal location string.

    Segments split on commas and on ' - ' (portals write 'Praha - Holešovice').
    Each segment yields itself and a house-number-stripped variant, so
    'Škarmanská 369 / 369, Domažlice, Plzeňský kraj' gives
    ['skarmanska 369 / 369', 'skarmanska', 'domazlice'] and 'Praha 7' gives
    ['praha 7', 'praha'].
    """
    segments = []
    for comma_part in location.split(","):
        segments.extend(re.split(r"\s+[-–]\s+", comma_part))
    names: list[str] = []
    for segment in segments:
        segment = segment.strip()
        # Regions are not in the gazetteer; 'Plzeňský kraj' would otherwise
        # normalize to a bare 'plzensky' that can shadow a real place name.
        if segment.casefold().endswith("kraj"):
            continue
        norm = normalize_name(segment)
        without_numbers = " ".join(_HOUSE_NUMBER.sub(" ", norm).split())
        for name in (norm, without_numbers):
            if name and name not in names:
                names.append(name)
    return names


class Gazetteer:
    """Read-only place lookups over the bundled gazetteer.

    Resolution runs three passes, each trying tiers most specific first.
    Pass 1, municipality agreement: a second candidate names the row's
    municipality ('Veletržní' + 'Praha') - street names repeat across the
    country ('U Studánky' exists 49 times), so a street alone proves little.
    Pass 2, district scope: a candidate naming an okres narrows the search
    to it, and a name unique within that okres resolves ('Škarmanská' +
    okres 'Domažlice' finds the street in Kdyně); several copies inside one
    okres stay ambiguous. Pass 3, unique name: every row of a candidate
    sits in one single municipality. Uniqueness counts distinct
    municipalities, not rows: a town and its self-named part ('Kdyně') are
    one place, while parts of the same name in two towns ('Holešovice' in
    Praha and in Chroustovice) are a real tie.

    district_labeled says the caller knows the location string names the
    okres where a town would normally stand (RE/MAX does this, always -
    'Nádražní 10, Klatovy' means a Nádražní somewhere in okres Klatovy, not
    the one in Klatovy town). District-named candidates then only scope and
    resolve as districts, never as towns. Anything still ambiguous resolves
    to None rather than a guess.
    """

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path(str(files("rentczecher.adapters.geocoding") / "gazetteer.sqlite"))
        # mode=ro: a plain connect() would create an empty database file
        # where the shipped one is missing instead of failing loudly.
        self._conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self._conn.row_factory = sqlite3.Row

    def _to_place(self, row: sqlite3.Row) -> ResolvedPlace:
        return ResolvedPlace(
            name=row["name"],
            muni_name=row["muni_name"],
            okres_name=row["okres_name"],
            tier=row["tier"],
            lat=row["lat"],
            lon=row["lon"],
        )

    def resolve(self, location: str, *, district_labeled: bool = False) -> ResolvedPlace | None:
        names = candidate_names(location)
        if not names:
            return None
        rows = self._rows_named(names)
        district_names = {r["name_norm"] for r in rows if r["tier"] == "district"}
        if district_labeled:
            # A district-named candidate is context only, never the town.
            rows = [r for r in rows
                    if r["name_norm"] not in district_names or r["tier"] == "district"]
        place_rows = [r for r in rows if r["tier"] != "district"]
        vouchers = set(names) - (district_names if district_labeled else set())

        match = (self._vouched_by_municipality(place_rows, vouchers)
                 or self._unique_in_named_district(place_rows, district_names)
                 or self._unique_name(place_rows)
                 or self._named_district(rows))
        return self._to_place(match) if match else None

    def _rows_named(self, names: list[str]) -> list[sqlite3.Row]:
        stmt = """
            SELECT name, name_norm, muni_name, muni_norm, muni_code,
                   okres_name, okres_norm, tier, lat, lon
            FROM places WHERE name_norm = ?
        """
        rows: list[sqlite3.Row] = []
        for name in names:
            rows.extend(self._conn.execute(stmt, (name,)).fetchall())
        return rows

    def _vouched_by_municipality(self, place_rows, vouchers) -> sqlite3.Row | None:
        """"Did the text name a street and its town?"""
        for tier in _TIERS_MOST_SPECIFIC_FIRST:
            agreeing = [r for r in place_rows if r["tier"] == tier
                        and r["muni_norm"] in vouchers - {r["name_norm"]}]
            if len(agreeing) == 1:
                return agreeing[0]
        return None

    def _unique_in_named_district(self, place_rows, district_names) -> sqlite3.Row | None:
        """The only place of its name inside a candidate-named okres."""
        for tier in _TIERS_MOST_SPECIFIC_FIRST:
            scoped = [r for r in place_rows if r["tier"] == tier
                      and r["okres_norm"] in district_names - {r["name_norm"]}]
            if len(scoped) == 1:
                return scoped[0]
        return None

    def _unique_name(self, place_rows) -> sqlite3.Row | None:
        """A name all of whose rows sit in one single municipality - a town
        and its self-named part are one place, not a tie."""
        by_name: dict[str, list[sqlite3.Row]] = {}
        for row in place_rows:
            by_name.setdefault(row["name_norm"], []).append(row)
        for tier in _TIERS_MOST_SPECIFIC_FIRST:
            for rows in by_name.values():
                if len({r["muni_code"] for r in rows}) != 1:
                    continue
                in_tier = [r for r in rows if r["tier"] == tier]
                if len(in_tier) == 1:
                    return in_tier[0]
        return None

    def _named_district(self, rows) -> sqlite3.Row | None:
        """Last resort: the named district itself, at its honest coarse tier."""
        districts = [r for r in rows if r["tier"] == "district"]
        if len(districts) == 1:
            return districts[0]
        return None
