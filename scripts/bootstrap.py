#!/usr/bin/env python3
"""One-command dev setup: checks required tools, then installs the Python
and GUI environments. Idempotent, rerun anytime.

Run: python3 scripts/bootstrap.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUI = REPO / "gui"


def run(*command: str, cwd: Path) -> None:
    where = "." if cwd == REPO else str(cwd.relative_to(REPO))
    print(f"\n$ {' '.join(command)}  (in {where})")
    subprocess.run(command, cwd=cwd, check=True)


def require(tool: str, install_hint: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"bootstrap: {tool} not found. Install it: {install_hint}")


def npm_floor() -> tuple[int, int]:
    declared = json.loads((GUI / "package.json").read_text())["engines"]["npm"]
    if not declared.startswith(">="):
        sys.exit(f'bootstrap: cannot read gui/package.json engines.npm {declared!r}, expected ">=X.Y"')
    major, minor = (int(part) for part in declared.removeprefix(">=").split(".")[:2])
    return major, minor


def npm_ci_command() -> list[str]:
    version = subprocess.run(
        ["npm", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    major, minor = (int(part) for part in version.split(".")[:2])
    if (major, minor) >= npm_floor():
        return ["npm", "ci"]
    # gui/.npmrc makes the engines floor fatal, so a system npm below it
    # borrows a current one for the install.
    return ["npx", "-y", "npm@10", "ci"]


def main() -> None:
    require("uv", "https://docs.astral.sh/uv/getting-started/installation/")
    require("node", "https://nodejs.org (18.17 or newer)")
    require("npm", "ships with node")

    run("uv", "sync", cwd=REPO)
    run("uv", "run", "prek", "install", cwd=REPO)
    run(*npm_ci_command(), cwd=GUI)
    # The generated catalog and API types are gitignored, so a fresh clone
    # needs one codegen pass before the editor sees a consistent tree.
    run("npm", "run", "codegen", cwd=GUI)

    env_file = GUI / ".env"
    if not env_file.exists():
        shutil.copy(GUI / ".env.example", env_file)
        print(f"\nCreated {env_file.relative_to(REPO)} from .env.example, adjust as needed.")

    print("\nbootstrap: ready.")


if __name__ == "__main__":
    main()
