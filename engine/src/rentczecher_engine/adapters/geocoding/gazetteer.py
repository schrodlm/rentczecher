"""Offline geocoding: scraped place names to coordinates, no network.

Lookups run against the shipped gazetteer.sqlite (built by the location
refresh script from the state address registry).
"""

import re
import sqlite3
import unicodedata
from collections.abc import Iterable
from dataclasses import replace
from importlib.resources import files
from pathlib import Path
from typing import TypeVar

from rentczecher_engine.domain.location import Location, ParsedPlace, Place

# Portals disagree on decoration: sreality "Hlavní město Praha" is remax
# and bezrealitky "Praha"; bezrealitky prefixes okresy with "okres".
# Hyphenated names (Brno-město) stay single words, untouched by this.
_NOISE_WORDS = {"okres", "kraj", "hlavni", "mesto"}


def normalize_name(name: str) -> str:
    """One key for all portals' (and users') spellings of a place: casefold,
    strip diacritics, drop the decoration words portals disagree on."""
    decomposed = unicodedata.normalize("NFD", name.casefold())
    flat = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return " ".join(w for w in flat.split() if w not in _NOISE_WORDS)


# Portals put a house number after the street name ("Škarmanská 369 / 369");
# the gazetteer knows streets, not buildings.
_HOUSE_NUMBER = re.compile(r"\b\d+[a-z]?(\s*/\s*\d+[a-z]?)?\b")

T = TypeVar("T")

_KINDS_MOST_SPECIFIC_FIRST = ("ulice", "cast_obce", "mestska_cast", "obec")

# The schema this code reads. The build stamps it into the file, and a file
# built for another schema is refused rather than misread.
SCHEMA_VERSION = 2


def open_gazetteer(db_path: Path | None = None) -> sqlite3.Connection:
    """A read-only connection to the gazetteer, the shipped one by default.
    A file built for another schema is refused rather than misread."""
    if db_path is None:
        db_path = Path(str(files("rentczecher_engine.adapters.geocoding") / "gazetteer.sqlite"))
    # mode=ro: a plain connect() would create an empty database file
    # where the shipped one is missing instead of failing loudly.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    stmt = "SELECT value FROM meta WHERE key = 'schema_version'"
    version = conn.execute(stmt).fetchone()
    if version is None or version["value"] != str(SCHEMA_VERSION):
        raise RuntimeError(f"the gazetteer at {db_path} has schema {version and version['value']}, "
                           f"this engine reads schema {SCHEMA_VERSION}: rebuild it")
    return conn


def candidate_names(names: Iterable[str]) -> list[str]:
    """Normalized lookup keys for scraped place names, most specific first.

    Each name yields itself and a house-number-stripped variant, so
    'Škarmanská 369 / 369' gives ['skarmanska 369 / 369', 'skarmanska'] and
    'Praha 7' gives ['praha 7', 'praha'].
    """
    candidates: list[str] = []
    for name in names:
        norm = normalize_name(name)
        without_numbers = " ".join(_HOUSE_NUMBER.sub(" ", norm).split())
        for candidate in (norm, without_numbers):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _to_place(row: sqlite3.Row) -> Place:
    return Place(code=row["code"], name=row["name"], lat=row["lat"], lon=row["lon"])


def _only(items: set[T]) -> T | None:
    if len(items) != 1:
        return None
    (item,) = items
    return item


class Gazetteer:
    """Answers "where is this?" for scraped place names, offline.

    The bundled file holds every Czech place a listing's text can name -
    ulice, část obce, městská část, obec and okres - each with its kind and
    RÚIAN code, a normalized name, its obec, its okres and a centre point.
    Resolving a ParsedPlace means picking exactly one of those rows, or
    refusing: a wrong place silently poisons everything built on top, so
    anything ambiguous resolves to None rather than a guess.

    The names carry no roles (see ParsedPlace): the same word can be a
    street, a town, the town's self-named part, or all of them at once.
    So every name is looked up across all tiers, everything lands in one
    candidate pool, and four passes look for a single row the evidence
    agrees on. The passes run in order of how much the answer can be
    trusted, each walking tiers most specific first, and each returns a
    row only when exactly one matches - two matches is a tie, and a tie
    falls through to the next, weaker pass:

    1. Municipality agreement: a second name vouches for the row's town.
       'Veletržní' exists in Praha and in Brno; 'Veletržní' + 'Praha'
       picks one. Street names repeat across the country ('U Studánky'
       exists 49 times), so a street alone proves little - two parts of
       one address agreeing is the strongest evidence there is.

    2. District scope: the okres narrows the map. No town named
       'Domažlice' has a Škarmanská street, but okres Domažlice contains
       exactly one, in Kdyně. Weaker than pass 1: a region vouched for
       the name, not the town itself. Several copies inside the okres
       stay a tie.

    3. Unique name: the name can only mean one place. Everything called
       'Kdyně' sits in a single municipality, so bare 'Kdyně' needs no
       witness. Uniqueness counts distinct municipalities, not rows - a
       town plus its self-named central part is one place at two tiers,
       while parts named 'Holešovice' in Praha and in Chroustovice are a
       real tie.

    4. The named district itself: the give-up-gracefully answer. When
       'Nádražní' repeats inside okres Klatovy no single street can be
       picked, but the okres is still certain, and a coarse true answer
       beats a precise wrong one. The result's most specific unit says
       how coarse. Callers gate on its kind.

    A stated district (ParsedPlace.district) changes exactly one thing:
    that name may scope (pass 2) and be the answer (pass 4) but never
    resolve as the same-named town - the caller has said which of the two
    readings it means, and every district capital shares its okres's name.
    Everything else is pooled: no name is ever routed to a specific pass
    or tier by where it came from, because a name's kind is discovered by
    lookup, never assumed.

    The winning row becomes a Location: its containing units are filled in,
    and the kinds it leaves open are completed from the other names, each
    looked up inside its obec.
    """

    def __init__(self, db_path: Path | None = None):
        self._conn = open_gazetteer(db_path)

    def resolve(self, place: ParsedPlace) -> Location | None:
        """The location the parsed names point to, or None when they are
        unknown or ambiguous."""
        candidates = candidate_names(place.names)
        stated = frozenset(candidate_names([place.district]) if place.district else ())
        lookup = candidates + [name for name in stated if name not in candidates]
        if not lookup:
            return None
        rows = self._rows_named(lookup)
        # A stated district is context only, never the same-named town.
        rows = [r for r in rows
                if r["name_norm"] not in stated or r["kind"] == "okres"]
        district_names = {r["name_norm"] for r in rows if r["kind"] == "okres"}
        place_rows = [r for r in rows if r["kind"] != "okres"]
        vouchers = set(candidates) - stated

        match = (self._vouched_by_municipality(place_rows, vouchers)
                 or self._unique_in_named_district(place_rows, district_names)
                 or self._unique_name(place_rows)
                 or self._named_district(rows))
        if match is None:
            return None
        return self._filled_from_names_inside_obec(self._location_of(match), place.names)

    def _filled_from_names_inside_obec(self, location: Location, names: Iterable[str]) -> Location:
        """The location with each kind the match left open filled from a name
        inside its obec. A kind two names disagree on stays open."""
        obec = location.obec
        if obec is None:
            return location
        # A name equal to the town's or the okres's own name states that
        # unit, never a same-named part inside the town.
        coarser_names = {normalize_name(obec.name)}
        if location.okres is not None:
            coarser_names.add(normalize_name(location.okres.name))

        obvody: set[Place] = set()
        mestske_casti: set[Place] = set()
        casti_obce: set[Place] = set()
        ulice: set[Place] = set()
        for name in names:
            candidates = candidate_names([name])
            # In Praha a district number names the obvod, as in a Czech
            # address.
            obvod = self._obvod_named_inside(obec, candidates)
            if obvod is not None:
                obvody.add(obvod)
                continue
            part_candidates = [c for c in candidates if c not in coarser_names]
            part = self._part_named_inside(obec, part_candidates)
            if part is None:
                continue
            kind, unit = part
            if kind == "mestska_cast":
                mestske_casti.add(unit)
                obvod_of_part = self._obvod_of_mestska_cast(unit.code)
                if obvod_of_part is not None:
                    obvody.add(obvod_of_part)
            elif kind == "cast_obce":
                casti_obce.add(unit)
            elif kind == "ulice":
                ulice.add(unit)
            else:
                raise ValueError(f"no location field for kind {kind!r}")
        return replace(
            location,
            obvod=location.obvod or _only(obvody),
            mestska_cast=location.mestska_cast or _only(mestske_casti),
            cast_obce=location.cast_obce or _only(casti_obce),
            ulice=location.ulice or _only(ulice),
        )

    def _obvod_named_inside(self, obec: Place, candidates: list[str]) -> Place | None:
        stmt = "SELECT code, name, lat, lon FROM obvody WHERE obec_code = ? AND name_norm = ?"
        for candidate in candidates:
            row = self._conn.execute(stmt, (obec.code, candidate)).fetchone()
            if row is not None:
                return _to_place(row)
        return None

    def _part_named_inside(self, obec: Place, candidates: list[str]) -> tuple[str, Place] | None:
        """The one městská část, část obce or street of the obec the
        candidates name, with its kind."""
        stmt = """
            SELECT kind, code, name, lat, lon FROM places
            WHERE obec_code = ? AND kind IN ('mestska_cast', 'cast_obce', 'ulice') AND name_norm = ?
        """
        parts = {(row["kind"], _to_place(row))
                 for candidate in candidates
                 for row in self._conn.execute(stmt, (obec.code, candidate))}
        return _only(parts)

    def candidate_names(self, names: Iterable[str]) -> list[str]:
        return candidate_names(names)

    def name_tiers(self, name: str, muni: str | None = None) -> frozenset[str]:
        """Tiers at which any place carries this name, ambiguity ignored.

        'Veletržní' is a street in Praha and in Brno - which one is unknown,
        but that it names a street is knowledge in itself. Callers weighing
        shared names need exactly that and nothing more.

        A municipality narrows the question to places inside it: nationally
        'Bubeneč' is both a part of Praha and a street (Lenešice named one
        after the neighborhood), but scoped to Praha the street reading
        disappears."""
        if muni is None:
            stmt = "SELECT DISTINCT kind FROM places WHERE name_norm = ?"
            scope: tuple[str, ...] = ()
        else:
            stmt = "SELECT DISTINCT kind FROM places WHERE name_norm = ? AND obec_norm = ?"
            scope = (normalize_name(muni),)
        tiers: set[str] = set()
        for candidate in candidate_names([name]):
            for row in self._conn.execute(stmt, (candidate, *scope)):
                tiers.add(row["kind"])
        return frozenset(tiers)

    def _location_of(self, row: sqlite3.Row) -> Location:
        """The matched unit in its kind's field, with its strict parents."""
        if row["kind"] == "okres":
            return self._okres_location(row["code"])
        location = self._obec_location(row["obec_code"])
        if row["kind"] == "obec":
            return location
        if row["kind"] == "ulice":
            return replace(location, ulice=_to_place(row))
        if row["kind"] == "cast_obce":
            # A část obce named after its obec: that name in a listing states
            # the obec, not the part.
            if row["name_norm"] == row["obec_norm"]:
                return location
            return replace(location, cast_obce=_to_place(row))
        if row["kind"] == "mestska_cast":
            return replace(location, mestska_cast=_to_place(row), obvod=self._obvod_of_mestska_cast(row["code"]))
        raise ValueError(f"no location field for kind {row['kind']!r}")

    def _okres_location(self, okres_code: int) -> Location:
        stmt = "SELECT code, name, lat, lon, kraj_code FROM okresy WHERE code = ?"
        row = self._conn.execute(stmt, (okres_code,)).fetchone()
        return Location(
            kraj=self._kraj(row["kraj_code"]),
            okres=_to_place(row),
            obec=None,
            obvod=None,
            mestska_cast=None,
            cast_obce=None,
            ulice=None,
        )

    def _obec_location(self, obec_code: int) -> Location:
        stmt = "SELECT code, name, lat, lon, okres_code, kraj_code FROM obce WHERE code = ?"
        row = self._conn.execute(stmt, (obec_code,)).fetchone()
        return Location(
            kraj=self._kraj(row["kraj_code"]),
            okres=self._okres(row["okres_code"]) if row["okres_code"] is not None else None,
            obec=_to_place(row),
            obvod=None,
            mestska_cast=None,
            cast_obce=None,
            ulice=None,
        )

    def _kraj(self, kraj_code: int) -> Place:
        stmt = "SELECT code, name, lat, lon FROM kraje WHERE code = ?"
        return _to_place(self._conn.execute(stmt, (kraj_code,)).fetchone())

    def _okres(self, okres_code: int) -> Place:
        stmt = "SELECT code, name, lat, lon FROM okresy WHERE code = ?"
        return _to_place(self._conn.execute(stmt, (okres_code,)).fetchone())

    def _obvod_of_mestska_cast(self, mestska_cast_code: int) -> Place | None:
        """The obvod a městská část lies in. Only Praha's do."""
        stmt = """
            SELECT ob.code, ob.name, ob.lat, ob.lon
            FROM mestske_casti m JOIN obvody ob ON ob.code = m.obvod_code
            WHERE m.code = ?
        """
        row = self._conn.execute(stmt, (mestska_cast_code,)).fetchone()
        return _to_place(row) if row is not None else None

    def _rows_named(self, names: list[str]) -> list[sqlite3.Row]:
        stmt = """
            SELECT kind, code, name, name_norm, obec_code, obec_norm, okres_norm, lat, lon
            FROM places WHERE name_norm = ?
        """
        rows: list[sqlite3.Row] = []
        for name in names:
            rows.extend(self._conn.execute(stmt, (name,)).fetchall())
        return rows

    def _vouched_by_municipality(self, place_rows, vouchers) -> sqlite3.Row | None:
        """Did a second name vouch for the row's town?"""
        for kind in _KINDS_MOST_SPECIFIC_FIRST:
            agreeing = [r for r in place_rows if r["kind"] == kind
                        and r["obec_norm"] in vouchers - {r["name_norm"]}]
            if len(agreeing) == 1:
                return agreeing[0]
        return None

    def _unique_in_named_district(self, place_rows, district_names) -> sqlite3.Row | None:
        """Is the name unique inside a named okres?"""
        for kind in _KINDS_MOST_SPECIFIC_FIRST:
            scoped = [r for r in place_rows if r["kind"] == kind
                      and r["okres_norm"] in district_names - {r["name_norm"]}]
            if len(scoped) == 1:
                return scoped[0]
        return None

    def _unique_name(self, place_rows) -> sqlite3.Row | None:
        """Can the name only mean one municipality?"""
        by_name: dict[str, list[sqlite3.Row]] = {}
        for row in place_rows:
            by_name.setdefault(row["name_norm"], []).append(row)
        for kind in _KINDS_MOST_SPECIFIC_FIRST:
            for rows in by_name.values():
                if len({r["obec_code"] for r in rows}) != 1:
                    continue
                in_kind = [r for r in rows if r["kind"] == kind]
                if len(in_kind) == 1:
                    return in_kind[0]
        return None

    def _named_district(self, rows) -> sqlite3.Row | None:
        """Give up gracefully: the named district itself."""
        districts = [r for r in rows if r["kind"] == "okres"]
        if len(districts) == 1:
            return districts[0]
        return None
