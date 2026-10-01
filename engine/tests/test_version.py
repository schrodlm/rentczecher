"""The app ships one product version. The desktop shell's tauri.conf.json
holds it, and the engine's pyproject.toml must carry the same number."""

import json
import tomllib
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent


def test_engine_version_matches_the_app_version():
    """pyproject.toml's version equals the app version in tauri.conf.json."""
    app_version = json.loads((ENGINE.parent / "shell" / "tauri.conf.json").read_text())["version"]
    engine_version = tomllib.loads((ENGINE / "pyproject.toml").read_text())["project"]["version"]
    assert engine_version == app_version
