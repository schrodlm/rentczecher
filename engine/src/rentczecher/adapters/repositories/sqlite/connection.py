import sqlite3
from pathlib import Path


def connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    # foreign_keys defaults OFF and is a no-op once a transaction is open, so
    # it must be set here, before any statement.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn
