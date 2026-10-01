"""Every test in this folder runs the frozen sidecar, so each is marked smoke
and left out of the default run. Freeze first, then run them with:
uv run python scripts/freeze_sidecar.py && uv run pytest -m smoke"""

from pathlib import Path

import pytest

SMOKE_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if SMOKE_DIR in item.path.parents:
            item.add_marker(pytest.mark.smoke)
