"""Apply numbered SQL migrations, tracking the applied version in
PRAGMA user_version."""

import re
import sqlite3
from pathlib import Path

from rentczecher_engine.adapters.repositories.sqlite import connection

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_FILENAME_RE = re.compile(r"^(\d+)_.*\.sql$")


def apply_pending(conn: sqlite3.Connection) -> list[int]:
    """Applies unapplied migration files in numerical order within atomic transactions.

    Returns the list of newly applied version numbers.
    """
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    applied = []
    for version, path in _pending(current):
        # Dropping a table to rebuild it would cascade-delete its child rows,
        # and the pragma is ignored inside a transaction, so it goes off first.
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            _apply(conn, version, path)
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
        applied.append(version)
    return applied


def _apply(conn: sqlite3.Connection, version: int, path: Path) -> None:
    """Raises IntegrityError, applying nothing, when the migration orphans a
    row. Rows orphaned before it ran do not count, so a migration that
    rebuilds a table keeps its rowids."""
    conn.execute("BEGIN")
    try:
        orphans_before = _orphans(conn)
        for statement in _split_statements(path.read_text(encoding="utf-8")):
            conn.execute(statement)
        orphans = _orphans(conn) - orphans_before
        if orphans:
            child_table, _rowid, parent_table = next(iter(orphans))
            raise sqlite3.IntegrityError(
                f"Migration {path.name} leaves {len(orphans)} row(s) in {child_table} "
                f"without their parent row in {parent_table}")
        # user_version takes no bound parameter; version is a validated
        # filename integer, not user input.
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _orphans(conn: sqlite3.Connection) -> set[tuple[str, int, str]]:
    """Each row without its parent row, as its table, rowid and parent table."""
    # Keyed without the foreign key's id, which a rebuild renumbers.
    return {(child_table, rowid, parent_table)
            for child_table, rowid, parent_table, _fk_id in conn.execute("PRAGMA foreign_key_check")}


def apply_pending_at(db_file: Path) -> list[int]:
    """apply_pending against a database path: creates the parent directory
    on first run and opens (and closes) its own connection."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = connection.connect(db_file)
    try:
        return apply_pending(conn)
    finally:
        conn.close()


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
