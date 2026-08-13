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
    muni_name: str
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

    Resolution runs two passes, each trying tiers most specific first.
    Pass 1, municipality agreement: a second candidate names the row's
    municipality ('Veletržní' + 'Praha') - street names repeat across the
    country ('U Studánky' exists 49 times), so a street alone proves little.
    Pass 2, unique name: every row of a candidate sits in one single
    municipality ('Škarmanská' occurs once countrywide) - portals sometimes
    put the district where the municipality belongs, so around a unique name
    the other labels cannot be trusted anyway. Uniqueness counts distinct
    municipalities, not rows: a town and its self-named part ('Kdyně') are
    one place, while parts of the same name in two towns ('Holešovice' in
    Praha and in Chroustovice) are a real tie. Anything still ambiguous
    resolves to None rather than a guess.
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
            tier=row["tier"],
            lat=row["lat"],
            lon=row["lon"],
        )

    def resolve(self, location: str) -> ResolvedPlace | None:
        names = candidate_names(location)
        if not names:
            return None
        stmt = """
            SELECT name, name_norm, muni_name, muni_norm, muni_code, tier, lat, lon
            FROM places WHERE name_norm = ?
        """
        rows_by_name = {
            name: self._conn.execute(stmt, (name,)).fetchall() for name in names
        }
        candidate_set = set(names)

        # Pass 1: municipality agreement. The vouching name must be a second
        # candidate - a lone 'Domažlice' may not vouch for itself.
        for tier in _TIERS_MOST_SPECIFIC_FIRST:
            agreeing = [
                row for rows in rows_by_name.values() for row in rows
                if row["tier"] == tier
                and row["muni_norm"] in candidate_set - {row["name_norm"]}
            ]
            if len(agreeing) == 1:
                return self._to_place(agreeing[0])

        # Pass 2: a name all of whose rows sit in one single municipality.
        for tier in _TIERS_MOST_SPECIFIC_FIRST:
            for name in names:
                rows = rows_by_name[name]
                if not rows:
                    continue
                if len({row["muni_code"] for row in rows}) != 1:
                    continue
                in_tier = [row for row in rows if row["tier"] == tier]
                if len(in_tier) == 1:
                    return self._to_place(in_tier[0])
        return None
