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
