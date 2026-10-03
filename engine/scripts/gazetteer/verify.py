"""Checks a built gazetteer before it may replace the shipped one. A
half-built or mis-joined file must abort, not ship."""

import sqlite3
from pathlib import Path

from .database import SCHEMA_VERSION

_EXPECTED_ROWS = {
    "kraje": (14, 14),
    "okresy": (70, 90),
    "obce": (6_000, 7_000),
    "obvody": (10, 10),
    "mestske_casti": (100, 200),
    "casti_obce": (14_000, 17_000),
    "ulice": (70_000, 100_000),
    "casti_obce_mestske_casti": (200, 1_000),
    "ulice_mestske_casti": (10_000, 30_000),
    "ulice_casti_obce": (60_000, 120_000),
}


def verify_gazetteer(path: Path) -> None:
    """Raises SystemExit naming every failed check."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        failures = _failures(conn)
    finally:
        conn.close()
    if failures:
        raise SystemExit("gazetteer verification failed:\n  " + "\n  ".join(failures))


def _failures(conn: sqlite3.Connection) -> list[str]:
    failures = []
    for table, (low, high) in _EXPECTED_ROWS.items():
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        if not low <= count <= high:
            failures.append(f"{table}: {count:,} rows, expected {low:,} to {high:,}")

    version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if version is None or version["value"] != str(SCHEMA_VERSION):
        failures.append(f"schema_version is {version and version['value']}, expected {SCHEMA_VERSION}")

    broken = conn.execute("PRAGMA foreign_key_check").fetchall()
    if broken:
        failures.append(f"{len(broken)} rows break a foreign key, e.g. {tuple(broken[0])}")

    stmt = """
        SELECT count(*) FROM obce o JOIN okresy ok ON ok.code = o.okres_code
        WHERE o.kraj_code <> ok.kraj_code
    """
    disagreeing = conn.execute(stmt).fetchone()[0]
    if disagreeing:
        failures.append(f"{disagreeing} obce name a kraj other than their okres's")

    stmt = "SELECT name FROM obce WHERE okres_code IS NULL"
    without_okres = [row["name"] for row in conn.execute(stmt)]
    if without_okres != ["Praha"]:
        failures.append(f"obce without an okres: {without_okres}, expected only Praha")

    failures.extend(_portal_coverage(conn))
    failures.extend(_known_places(conn))
    return failures


def _portal_coverage(conn: sqlite3.Connection) -> list[str]:
    """Every portal maps every kraj, okres and obvod, since a profile may
    search any of them."""
    kraje = conn.execute("SELECT count(*) FROM kraje").fetchone()[0]
    districts = conn.execute("SELECT (SELECT count(*) FROM okresy) + (SELECT count(*) FROM obvody)").fetchone()[0]
    stmt = """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND (name GLOB '*_regions' OR name GLOB '*_districts')
        ORDER BY name
    """
    failures = []
    for row in conn.execute(stmt).fetchall():
        expected = kraje if row["name"].endswith("_regions") else districts
        count = conn.execute(f"SELECT count(*) FROM {row['name']}").fetchone()[0]
        if count != expected:
            failures.append(f"{row['name']}: {count} rows, expected {expected}")
    return failures


def _known_places(conn: sqlite3.Connection) -> list[str]:
    """Facts about real places the build must reproduce."""
    failures = []
    stmt = """
        SELECT ob.name AS obvod, c.name AS cast_obce
        FROM ulice u
        JOIN obce o ON o.code = u.obec_code
        JOIN ulice_casti_obce uc ON uc.ulice_code = u.code
        JOIN casti_obce c ON c.code = uc.cast_obce_code
        JOIN ulice_mestske_casti um ON um.ulice_code = u.code
        JOIN mestske_casti m ON m.code = um.mestska_cast_code
        JOIN obvody ob ON ob.code = m.obvod_code
        WHERE u.name_norm = 'pristavni' AND o.name = 'Praha'
    """
    found = {(row["obvod"], row["cast_obce"]) for row in conn.execute(stmt)}
    if found != {("Praha 7", "Holešovice")}:
        failures.append(f"Přístavní lies in {found}, expected only Holešovice in Praha 7")

    stmt = """
        SELECT ok.name FROM obce o JOIN okresy ok ON ok.code = o.okres_code
        WHERE o.name_norm = 'kdyne'
    """
    okresy = [row["name"] for row in conn.execute(stmt)]
    if okresy != ["Domažlice"]:
        failures.append(f"Kdyně lies in okresy {okresy}, expected Domažlice")

    stmt = """
        SELECT k.name FROM obce o JOIN kraje k ON k.code = o.kraj_code
        WHERE o.name = 'Praha'
    """
    kraj = conn.execute(stmt).fetchone()
    if kraj is None or kraj["name"] != "Hlavní město Praha":
        failures.append(f"Praha lies in kraj {kraj and kraj['name']}, expected Hlavní město Praha")

    stmt = """
        SELECT DISTINCT ob.name FROM casti_obce c
        JOIN casti_obce_mestske_casti cm ON cm.cast_obce_code = c.code
        JOIN mestske_casti m ON m.code = cm.mestska_cast_code
        JOIN obvody ob ON ob.code = m.obvod_code
        WHERE c.name = 'Bubeneč'
    """
    obvody = sorted(row["name"] for row in conn.execute(stmt))
    if obvody != ["Praha 6", "Praha 7"]:
        failures.append(f"Bubeneč touches obvody {obvody}, expected Praha 6 and Praha 7")
    return failures
