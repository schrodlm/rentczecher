"""Test-suite-wide isolation from the real data directory.

Some modules resolve a data path into a module-level constant at import
time (e.g. cli.main.PID_PATH), so a per-test env fixture would apply too
late. Setting the environment here, at module scope, runs before
pytest imports any test module.
"""

import os
import tempfile

_root = tempfile.mkdtemp(prefix="rentczecher-test-")
# A repo-local database would win over the XDG home, so the override is set
# outright rather than left to resolution.
os.environ["RENTCZECHER_DATA_DIR"] = os.path.join(_root, "data")

# Imported after the environment redirect above on purpose: repository
# modules resolve nothing at import time, but the ordering keeps every
# rentczecher_engine import in this process behind the isolation.
import pytest  # noqa: E402

from rentczecher_engine.adapters.repositories.sqlite import connection, migrate  # noqa: E402
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore  # noqa: E402


@pytest.fixture
def run_store(tmp_path):
    """A SqliteRunStore over a temp database, plus its raw connection."""
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    return SqliteRunStore(conn), conn
