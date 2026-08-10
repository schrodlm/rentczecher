"""Apply numbered SQL migrations, tracking the applied version in
PRAGMA user_version."""

import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_FILENAME_RE = re.compile(r"^(\d+)_.*\.sql$")


def apply_pending(conn: sqlite3.Connection) -> list[int]:
    """Applies unapplied migration files in numerical order within atomic transactions.

    Returns the list of newly applied version numbers.
    """
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    applied = []
    for version, path in _pending(current):
        conn.execute("BEGIN")
        try:
            for statement in _split_statements(path.read_text()):
                conn.execute(statement)
            # user_version takes no bound parameter; version is a validated
            # filename integer, not user input.
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied.append(version)
    return applied


def _pending(current_version: int) -> list[tuple[int, Path]]:
    migrations = []
    for path in MIGRATIONS_DIR.iterdir():
        match = _FILENAME_RE.match(path.name)
        if match and int(match.group(1)) > current_version:
            migrations.append((int(match.group(1)), path))
    return sorted(migrations)


def _split_statements(sql: str) -> list[str]:
    # executescript() gives no atomicity (it commits per statement), so
    # statements run individually — and SQLite's own parser decides where each
    # ends, since a naive ';' split breaks on comments and quoted text.
    statements = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    # A leftover of only whitespace or -- comments (e.g. a trailing note after
    # the last ';') is not an incomplete statement.
    leftover = "\n".join(
        line for line in buffer.splitlines() if not line.lstrip().startswith("--"))
    if leftover.strip():
        raise ValueError(f"Migration file ends with incomplete SQL statement: {buffer.strip()[:60]}")
    return statements
