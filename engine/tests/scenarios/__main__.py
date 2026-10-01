"""Replays one scenario into a data folder for the app to open, replacing
whatever an earlier replay left there:
uv run python -m tests.scenarios <name> <folder>"""

import argparse
import shutil
from pathlib import Path

from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from tests.scenarios import Scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a scenario into a data folder")
    parser.add_argument("name", choices=Scenario.names())
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    shutil.rmtree(args.folder, ignore_errors=True)
    Scenario.load(args.name).replay_into(args.folder, utc_now())
    print(f"scenario {args.name} replayed into {args.folder}")


if __name__ == "__main__":
    main()
