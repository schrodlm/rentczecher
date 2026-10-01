"""The frozen sidecar, started the way the shell starts it. They scrape
nothing, so they pass on networks the portals block, CI runners included."""

import json
import os
import queue
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest


ENGINE = Path(__file__).resolve().parent.parent.parent
FROZEN = ENGINE.parent / "shell" / "sidecar" / "rentczecher-sidecar"
EXECUTABLE = FROZEN / ("rentczecher-sidecar.exe" if sys.platform == "win32" else "rentczecher-sidecar")

# A first launch can be slow while antivirus scans the freshly built files.
PORT_TIMEOUT_S = 60.0
# The port is bound before the app finishes starting, so health is polled
# until it answers, as the shell does.
HEALTH_TIMEOUT_S = 30.0
HEALTH_POLL_INTERVAL_S = 0.25
EXIT_TIMEOUT_S = 10.0


class RunningSidecar:
    """The frozen engine with a fresh token, a throwaway data directory and
    the example config, its stdin held open like the shell's."""

    def __init__(self, home: Path) -> None:
        config = home / "config.yaml"
        shutil.copy(ENGINE / "config.example.yaml", config)
        self.token = secrets.token_hex(32)
        env = {
            **os.environ,
            "RENTCZECHER_API_TOKEN": self.token,
            "RENTCZECHER_CONFIG": str(config),
            "RENTCZECHER_DATA_DIR": str(home / "data"),
        }
        self.process = subprocess.Popen(
            [str(EXECUTABLE), "serve", "--port", "0", "--exit-with-parent"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=env, text=True)
        self._lines: queue.Queue[str | None] = queue.Queue()
        threading.Thread(target=self._drain_stdout, daemon=True).start()
        self.port = self._wait_for_port()

    def _drain_stdout(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._lines.put(line.rstrip("\n"))
        self._lines.put(None)

    def _wait_for_port(self) -> int:
        deadline = time.monotonic() + PORT_TIMEOUT_S
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                break
            if line is None:
                pytest.fail(f"the sidecar exited with {self.process.wait()} before announcing a port")
            if line.startswith("PORT="):
                return int(line.removeprefix("PORT="))
        pytest.fail(f"no PORT line within {PORT_TIMEOUT_S:.0f} s")

    def get(self, path: str) -> object:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read())

    def wait_for_health(self) -> object:
        deadline = time.monotonic() + HEALTH_TIMEOUT_S
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                pytest.fail(f"the sidecar exited with {self.process.returncode} before answering health")
            try:
                return self.get("/v1/health")
            except urllib.error.URLError:
                time.sleep(HEALTH_POLL_INTERVAL_S)
        pytest.fail(f"health did not answer within {HEALTH_TIMEOUT_S:.0f} s")

    def close_stdin(self) -> None:
        assert self.process.stdin is not None
        self.process.stdin.close()

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()


@pytest.fixture
def sidecar(tmp_path: Path) -> Iterator[RunningSidecar]:
    if not EXECUTABLE.is_file():
        pytest.fail(f"no frozen sidecar at {EXECUTABLE}, run scripts/freeze_sidecar.py first")
    running = RunningSidecar(tmp_path)
    yield running
    running.stop()


def test_the_freeze_ships_the_gazetteer():
    """The gazetteer is a package data file, not an import, so the freeze
    recipe must collect it explicitly."""
    assert (FROZEN / "_internal" / "rentczecher_engine" / "adapters" / "geocoding" / "gazetteer.sqlite").is_file()


def test_the_sidecar_answers_health_with_its_token(sidecar):
    """The announced port serves the API, and the token from the
    environment authorizes it."""
    assert sidecar.wait_for_health() == []


def test_the_sidecar_serves_the_configured_profiles(sidecar):
    """The frozen engine reads its config and serves it, which needs the
    config schema, the migrations and the location table inside the freeze."""
    sidecar.wait_for_health()
    profiles = sidecar.get("/v1/profiles")
    assert isinstance(profiles, list) and len(profiles) > 0


def test_the_sidecar_exits_when_its_stdin_closes(sidecar):
    """The dead-man's switch: when the spawner dies, the OS closes the
    engine's stdin and the engine shuts down cleanly."""
    sidecar.wait_for_health()
    sidecar.close_stdin()
    assert sidecar.process.wait(timeout=EXIT_TIMEOUT_S) == 0
