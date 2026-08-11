"""Config and data location resolution.

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
    lives in <root>/src/rentczecher/.
    """
    return Path(__file__).resolve().parents[4]


def _xdg_dir(variable: str, default: Path) -> Path:
    # The XDG spec requires ignoring non-absolute values.
    value = os.environ.get(variable, "")
    if value and Path(value).is_absolute():
        return Path(value)
    return default


def _xdg_config_home() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", Path.home() / ".config")


def _xdg_data_home() -> Path:
    return _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share")


def _tier() -> str:
    """Where config and data live when no env override is set.

    The config file is the anchor: data follows it so one installation never
    splits across XDG and repo-local homes (e.g. a deleted data/ next to a
    repo-local config must not silently move state under ~/.local/share).
    Fresh setups, with no config anywhere, land on XDG.
    """
    if (_xdg_config_home() / APP_NAME / "config.yaml").exists():
        return "xdg"
    if (repo_root() / "config.yaml").exists():
        return "repo"
    return "xdg"


def config_path() -> Path:
    env = os.environ.get("RENTCZECHER_CONFIG")
    if env:
        return Path(env).expanduser()
    if _tier() == "repo":
        return repo_root() / "config.yaml"
    return _xdg_config_home() / APP_NAME / "config.yaml"


def data_dir() -> Path:
    env = os.environ.get("RENTCZECHER_DATA_DIR")
    if env:
        return Path(env).expanduser()
    config_override = os.environ.get("RENTCZECHER_CONFIG")
    if config_override:
        # Data follows the explicitly chosen config, so a single override
        # cannot split one installation across two homes.
        return Path(config_override).expanduser().parent / "data"
    if _tier() == "repo":
        return repo_root() / "data"
    return _xdg_data_home() / APP_NAME


def pid_lock_path() -> Path:
    return data_dir() / "watchdog.pid"


def db_path() -> Path:
    return data_dir() / "rentczecher.db"
