"""Every test in this folder hits a real portal, so each is marked live and
left out of the default run. Run them with: uv run pytest -m live"""

from pathlib import Path

import pytest

LIVE_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if LIVE_DIR in item.path.parents:
            item.add_marker(pytest.mark.live)
