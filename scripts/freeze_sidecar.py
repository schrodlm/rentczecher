#!/usr/bin/env python3
"""Freezes the engine into the desktop app's sidecar folder, where the shell's
bundle picks it up. PyInstaller builds only for the OS it runs on.

Run: uv run python scripts/freeze_sidecar.py
"""

from pathlib import Path

import PyInstaller.__main__

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    PyInstaller.__main__.run([
        str(REPO / "scripts" / "sidecar.spec"),
        "--distpath", str(REPO / "gui" / "src-tauri" / "sidecar"),
        "--workpath", str(REPO / "build" / "pyinstaller"),
        "--noconfirm",
    ])


if __name__ == "__main__":
    main()
