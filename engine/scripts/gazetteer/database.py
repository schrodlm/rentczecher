"""Writes the gazetteer file: creates the schema and stores the places."""

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .model import CastObce, Kraj, MestskaCast, Obec, Obvod, Okres, Overlaps, Ulice
from rentczecher_engine.adapters.scrapers.location_resolver import normalize_name

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Bumped on every schema change. The engine refuses a gazetteer whose version
# differs from the one it was written for.
SCHEMA_VERSION = 2


class GazetteerDatabase:
    """A gazetteer file being written. Inserts do not commit: the build
    commits once, after everything is in, so a failed build leaves nothing
    half-written behind."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @classmethod
    def create(cls, path: Path) -> "GazetteerDatabase":
        """A new, empty gazetteer at path, replacing any file there."""
        path.unlink(missing_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        database = cls(conn)
        database.set_meta("schema_version", str(SCHEMA_VERSION))
        return database

    def set_meta(self, key: str, value: str) -> None:
        stmt = "INSERT INTO meta (key, value) VALUES (?, ?)"
        self._conn.execute(stmt, (key, value))

    def insert_kraje(self, kraje: Iterable[Kraj]) -> None:
        stmt = """
            INSERT INTO kraje (code, name, name_norm, lat, lon)
            VALUES (?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (kraj.code, kraj.name, normalize_name(kraj.name), kraj.position.lat, kraj.position.lon)
            for kraj in kraje
        ))

    def insert_okresy(self, okresy: Iterable[Okres]) -> None:
        stmt = """
            INSERT INTO okresy (code, name, name_norm, kraj_code, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (okres.code, okres.name, normalize_name(okres.name), okres.kraj_code,
             okres.position.lat, okres.position.lon)
            for okres in okresy
        ))

    def insert_obce(self, obce: Iterable[Obec]) -> None:
        stmt = """
            INSERT INTO obce (code, name, name_norm, okres_code, kraj_code, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (obec.code, obec.name, normalize_name(obec.name), obec.okres_code, obec.kraj_code,
             obec.position.lat, obec.position.lon)
            for obec in obce
        ))

    def insert_obvody(self, obvody: Iterable[Obvod]) -> None:
        stmt = """
            INSERT INTO obvody (code, name, name_norm, obec_code, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (obvod.code, obvod.name, normalize_name(obvod.name), obvod.obec_code,
             obvod.position.lat, obvod.position.lon)
            for obvod in obvody
        ))

    def insert_mestske_casti(self, mestske_casti: Iterable[MestskaCast]) -> None:
        stmt = """
            INSERT INTO mestske_casti (code, name, name_norm, obec_code, obvod_code, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (mestska_cast.code, mestska_cast.name, normalize_name(mestska_cast.name),
             mestska_cast.obec_code, mestska_cast.obvod_code,
             mestska_cast.position.lat, mestska_cast.position.lon)
            for mestska_cast in mestske_casti
        ))

    def insert_casti_obce(self, casti_obce: Iterable[CastObce]) -> None:
        stmt = """
            INSERT INTO casti_obce (code, name, name_norm, obec_code, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (cast_obce.code, cast_obce.name, normalize_name(cast_obce.name), cast_obce.obec_code,
             cast_obce.position.lat, cast_obce.position.lon)
            for cast_obce in casti_obce
        ))

    def insert_ulice(self, ulice: Iterable[Ulice]) -> None:
        stmt = """
            INSERT INTO ulice (code, name, name_norm, obec_code, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._conn.executemany(stmt, (
            (street.code, street.name, normalize_name(street.name), street.obec_code,
             street.position.lat, street.position.lon)
            for street in ulice
        ))

    def insert_overlaps(self, overlaps: Overlaps) -> None:
        stmt = """
            INSERT INTO casti_obce_mestske_casti (cast_obce_code, mestska_cast_code)
            VALUES (?, ?)
        """
        self._conn.executemany(stmt, sorted(overlaps.casti_obce_mestske_casti))
        stmt = """
            INSERT INTO ulice_mestske_casti (ulice_code, mestska_cast_code)
            VALUES (?, ?)
        """
        self._conn.executemany(stmt, sorted(overlaps.ulice_mestske_casti))
        stmt = """
            INSERT INTO ulice_casti_obce (ulice_code, cast_obce_code)
            VALUES (?, ?)
        """
        self._conn.executemany(stmt, sorted(overlaps.ulice_casti_obce))

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
