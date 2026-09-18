"""Test-suite-wide isolation from real config and data paths.

Some modules resolve a config/data path into a module-level constant at
import time (e.g. legacy_json_db.DATA_DIR), so a per-test env fixture would
apply too late. Setting the environment here, at module scope, runs before
pytest imports any test module.
"""

import os
import tempfile

_root = tempfile.mkdtemp(prefix="rentczecher-test-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_root, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(_root, "data")
os.environ.pop("RENTCZECHER_CONFIG", None)
os.environ.pop("RENTCZECHER_DATA_DIR", None)

# Imported after the environment redirect above on purpose: repository
# modules resolve nothing at import time, but the ordering keeps every
# rentczecher import in this process behind the isolation.
import pytest  # noqa: E402

from rentczecher.adapters.repositories.sqlite import connection, migrate  # noqa: E402
from rentczecher.adapters.repositories.sqlite.store import SqliteRunStore  # noqa: E402


@pytest.fixture
def run_store(tmp_path):
    """A SqliteRunStore over a temp database, plus its raw connection."""
    conn = connection.connect(tmp_path / "t.db")
    migrate.apply_pending(conn)
    return SqliteRunStore(conn), conn
