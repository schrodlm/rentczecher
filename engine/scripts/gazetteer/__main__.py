"""Builds the shipped gazetteer from RÚIAN and the portals.

Run from engine/: uv run python -m scripts.gazetteer build
"""

import argparse
import shutil
import tempfile
from pathlib import Path

import httpx

from .build import build_gazetteer
from .harvest import harvest_portals
from .portals.bezrealitky import Bezrealitky
from .portals.remax import Remax
from .portals.sreality import Sreality
from .sources import download_sources
from .verify import verify_gazetteer

SHIPPED_PATH = (Path(__file__).resolve().parents[2]
                / "src" / "rentczecher_engine" / "adapters" / "geocoding" / "gazetteer.sqlite")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the gazetteer from RÚIAN and the portals")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build the gazetteer from RÚIAN and the portals")
    build.add_argument("--state-file", type=Path, help="a downloaded ST_UZSZ zip instead of fetching it")
    build.add_argument("--address-dump", type=Path, help="a downloaded OB_ADR zip instead of fetching it")
    build.add_argument("--out", type=Path, default=SHIPPED_PATH, help="where to write (default: the shipped file)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        state_file, address_dump = args.state_file, args.address_dump
        if state_file is None or address_dump is None:
            downloaded_state, downloaded_dump = download_sources(Path(tmp))
            state_file = state_file or downloaded_state
            address_dump = address_dump or downloaded_dump
        built = Path(tmp) / "gazetteer.sqlite"
        build_gazetteer(state_file, address_dump, built)
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            harvest_portals(built, client, [Sreality(), Remax(), Bezrealitky()])
        verify_gazetteer(built)
        shutil.copyfile(built, args.out)
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
