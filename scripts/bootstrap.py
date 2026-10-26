#!/usr/bin/env python3
"""One-command dev setup: checks required tools, then installs the Python
and panel environments. Idempotent, rerun anytime.

Run: python3 scripts/bootstrap.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "engine"
PANEL = REPO / "panel"
SIDECAR = REPO / "shell" / "sidecar"


def run(*command: str, cwd: Path) -> None:
    where = "." if cwd == REPO else str(cwd.relative_to(REPO))
    print(f"\n$ {' '.join(command)}  (in {where})")
    subprocess.run(command, cwd=cwd, check=True)


def require(tool: str, install_hint: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"bootstrap: {tool} not found. Install it: {install_hint}")


# The system libraries the desktop shell compiles against on Linux, by their
# pkg-config names. Windows and macOS ship their webview with the OS.
LINUX_SHELL_LIBRARIES = ["webkit2gtk-4.1", "ayatana-appindicator3-0.1", "librsvg-2.0"]
DEBIAN_SHELL_PACKAGES = "libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev libxdo-dev"


def require_linux_shell_libraries() -> None:
    if not sys.platform.startswith("linux"):
        return
    require("pkg-config", "your distribution's pkg-config package")
    missing = [library for library in LINUX_SHELL_LIBRARIES
               if subprocess.run(["pkg-config", "--exists", library]).returncode != 0]
    if missing:
        sys.exit(
            f"bootstrap: the desktop shell needs {', '.join(missing)}. On Debian or Ubuntu: "
            f"sudo apt install {DEBIAN_SHELL_PACKAGES}. Other distributions: "
            "https://v2.tauri.app/start/prerequisites/")


def major_minor(version: str) -> tuple[int, int]:
    major, minor = (int(part) for part in version.split(".")[:2])
    return major, minor


def version_of(tool: str) -> tuple[int, int]:
    output = subprocess.run(
        [tool, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    return major_minor(output.removeprefix("v"))


def range_admits(declared: str, version: tuple[int, int]) -> bool:
    for alternative in declared.split("||"):
        alternative = alternative.strip()
        if alternative.startswith("^"):
            floor = major_minor(alternative.removeprefix("^"))
            if version[0] == floor[0] and version >= floor:
                return True
        elif alternative.startswith(">="):
            if version >= major_minor(alternative.removeprefix(">=")):
                return True
        else:
            sys.exit(f'bootstrap: cannot read engines range {declared!r}, expected "^X.Y" or ">=X.Y" alternatives')
    return False


def panel_engines() -> dict[str, str]:
    return json.loads((PANEL / "package.json").read_text())["engines"]


def require_node_version() -> None:
    declared = panel_engines()["node"]
    node = version_of("node")
    if not range_admits(declared, node):
        sys.exit(
            f"bootstrap: node {node[0]}.{node[1]} is too old, the panel and site need {declared}. "
            "Upgrade it: https://nodejs.org (the current LTS works)")


def npm_ci_command() -> list[str]:
    if range_admits(panel_engines()["npm"], version_of("npm")):
        return ["npm", "ci"]
    # panel/.npmrc makes the engines floor fatal, so a system npm below it
    # borrows a current one for the install.
    return ["npx", "-y", "npm@10", "ci"]


def main() -> None:
    require("uv", "https://docs.astral.sh/uv/getting-started/installation/")
    require("node", "https://nodejs.org")
    require_node_version()
    require("cargo", "https://rustup.rs")
    require_linux_shell_libraries()
    require("npm", "ships with node")

    run("uv", "sync", cwd=ENGINE)
    run("uv", "run", "prek", "install", cwd=ENGINE)
    run(*npm_ci_command(), cwd=PANEL)
    # The generated catalog and API types are gitignored, so a fresh clone
    # needs one codegen pass before the editor sees a consistent tree.
    run("npm", "run", "codegen", cwd=PANEL)
    # The shell bundles the frozen engine from this gitignored folder, and its
    # build fails when the folder is missing, even in dev, which runs the
    # engine from source and never reads it.
    SIDECAR.mkdir(exist_ok=True)

    print("\nbootstrap: ready.")


if __name__ == "__main__":
    main()
