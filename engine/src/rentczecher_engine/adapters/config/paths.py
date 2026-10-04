"""Data location resolution.

The data directory is RENTCZECHER_DATA_DIR when set, else the repository's
data/ directory when it already holds a database, else the XDG data home.

Every function reads the environment and filesystem at call time; processes
that must not change locations mid-flight (cron runs, a future GUI) should
capture the results once at startup.
"""

import os
from pathlib import Path

APP_NAME = "rentczecher"


def repo_root() -> Path:
    """Absolute path to the repository root.

    Resolves correctly only under an editable install, where the package
    lives in <root>/src/rentczecher_engine/.
    """
    return Path(__file__).resolve().parents[4]


def _xdg_data_home() -> Path:
    # The XDG spec requires ignoring non-absolute values.
    value = os.environ.get("XDG_DATA_HOME", "")
    if value and Path(value).is_absolute():
        return Path(value)
    return Path.home() / ".local" / "share"


def data_dir() -> Path:
    env = os.environ.get("RENTCZECHER_DATA_DIR")
    if env:
        return Path(env).expanduser()
    repo_data = repo_root() / "data"
    if (repo_data / "rentczecher.db").is_file():
        return repo_data
    return _xdg_data_home() / APP_NAME


def pid_lock_path() -> Path:
    return data_dir() / "watchdog.pid"


def db_path() -> Path:
    return data_dir() / "rentczecher.db"
