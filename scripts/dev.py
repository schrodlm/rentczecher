#!/usr/bin/env python3
"""Runs the dev pair: the sidecar and the panel's Vite server, both fed the
same token and port from gui/.env. Ctrl-C stops both.

Run: python3 scripts/dev.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
GUI = REPO / "gui"
ENV_FILE = GUI / ".env"


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def main() -> None:
    if not ENV_FILE.exists():
        sys.exit("dev: gui/.env is missing, run python3 scripts/bootstrap.py first")
    env_values = read_env(ENV_FILE)
    token = env_values.get("PUBLIC_SIDECAR_TOKEN")
    base_url = env_values.get("PUBLIC_SIDECAR_BASE_URL", "")
    if not token:
        sys.exit("dev: PUBLIC_SIDECAR_TOKEN missing from gui/.env")
    port = urlsplit(base_url).port
    if port is None:
        sys.exit(f"dev: PUBLIC_SIDECAR_BASE_URL carries no port: {base_url!r}")

    # Each child gets its own process group: npm runs vite as a grandchild,
    # so terminating npm alone would orphan the actual server. Teardown
    # kills the whole group instead.
    sidecar = subprocess.Popen(
        [
            "uv", "run", "rentczecher", "serve", "--port", str(port),
            "--allow-origin", "http://localhost:5173",
            "--allow-origin", "http://127.0.0.1:5173",
        ],
        cwd=REPO,
        env={**os.environ, "RENTCZECHER_API_TOKEN": token},
        start_new_session=True,
    )
    panel = subprocess.Popen(["npm", "run", "dev"], cwd=GUI, start_new_session=True)
    processes = {"sidecar": sidecar, "panel": panel}

    try:
        while True:
            for name, process in processes.items():
                code = process.poll()
                if code is not None:
                    raise SystemExit(f"dev: {name} exited with code {code}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\ndev: stopping both")
    finally:
        for process in processes.values():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        for process in processes.values():
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
