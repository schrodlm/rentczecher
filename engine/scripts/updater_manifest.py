#!/usr/bin/env python3
"""Writes the update manifest a release publishes as latest.json: for every
kind of installer the release ships, where the app downloads its update and
the signature the app checks the download against. Run in the release job,
on the folder of named installers and their .sig files.

Run: python3 engine/scripts/updater_manifest.py <release folder> <tag> <owner/repo>
"""

import base64
import binascii
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TAURI_CONFIG = REPO / "shell" / "tauri.conf.json"


@dataclass(frozen=True)
class UpdaterTarget:
    # The key the app looks itself up by: its OS, its architecture and the
    # kind of installer it was installed from.
    platform: str
    # The installer's name in the release.
    asset: str


TARGETS = [
    UpdaterTarget(platform="linux-x86_64-appimage", asset="rentczecher-linux-x86_64.AppImage"),
    UpdaterTarget(platform="linux-x86_64-deb", asset="rentczecher-linux-amd64.deb"),
    UpdaterTarget(platform="windows-x86_64-nsis", asset="rentczecher-windows-x64-setup.exe"),
    UpdaterTarget(platform="darwin-aarch64-app", asset="rentczecher-macos-arm64.app.tar.gz"),
]


class ManifestError(Exception):
    """Raised when the release cannot be offered as an update as it is."""


def key_id(encoded: str) -> bytes:
    """The id of the key behind a minisign public key or signature, each as
    Tauri stores it: the whole minisign text, base64 encoded. The id is the
    eight bytes after the two naming the algorithm, on the text's second line."""
    try:
        lines = base64.b64decode(encoded, validate=True).decode().splitlines()
        return base64.b64decode(lines[1], validate=True)[2:10]
    except (binascii.Error, UnicodeDecodeError, IndexError) as error:
        raise ManifestError(f"not a minisign key or signature: {error}") from error


def build_manifest(release: Path, tag: str, repo: str, published: datetime, public_key: str) -> dict[str, object]:
    """Fails when any installer or its signature is missing, since the app
    refuses a whole manifest that has one incomplete entry, and when a
    signature was made with another key than the one the app trusts, since
    the signing step only warns about that."""
    if not tag.startswith("v"):
        raise ManifestError(f"a release tag starts with v, not {tag!r}")
    trusted = key_id(public_key)
    platforms: dict[str, dict[str, str]] = {}
    for target in TARGETS:
        installer = release / target.asset
        signature_file = release / f"{target.asset}.sig"
        for path in (installer, signature_file):
            if not path.is_file():
                raise ManifestError(f"{path} is missing")
        signature = signature_file.read_text().strip()
        if key_id(signature) != trusted:
            raise ManifestError(f"{signature_file} was signed with another key than the app trusts")
        platforms[target.platform] = {
            # The tag's own download, never latest/, so the file always
            # matches the signature listed beside it.
            "url": f"https://github.com/{repo}/releases/download/{tag}/{target.asset}",
            "signature": signature,
        }
    return {
        "version": tag.removeprefix("v"),
        "pub_date": published.isoformat(timespec="seconds"),
        "platforms": platforms,
    }


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    release, tag, repo = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    public_key = json.loads(TAURI_CONFIG.read_text())["plugins"]["updater"]["pubkey"]
    try:
        manifest = build_manifest(release, tag, repo, datetime.now(UTC), public_key)
    except ManifestError as error:
        sys.exit(f"updater_manifest: {error}")
    (release / "latest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
