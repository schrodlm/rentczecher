import base64
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.updater_manifest import TAURI_CONFIG, TARGETS, ManifestError, build_manifest, key_id

REPO = "schrodlm/rentczecher"
PUBLISHED = datetime(2026, 10, 26, 17, 30, tzinfo=UTC)
APP_KEY = b"\x01\x02\x03\x04\x05\x06\x07\x08"
OTHER_KEY = b"\x09\x09\x09\x09\x09\x09\x09\x09"


def _minisign(comment: str, key: bytes, payload_length: int) -> str:
    """A key or signature as Tauri stores one: the minisign text, base64
    encoded, whose second line carries the algorithm, the key id and the
    payload."""
    second_line = base64.b64encode(b"Ed" + key + b"\x00" * payload_length).decode()
    return base64.b64encode(f"untrusted comment: {comment}\n{second_line}\n".encode()).decode()


PUBLIC_KEY = _minisign("minisign public key", APP_KEY, 32)


def _release(tmp_path: Path, key: bytes = APP_KEY) -> Path:
    for target in TARGETS:
        (tmp_path / target.asset).write_bytes(b"installer")
        (tmp_path / f"{target.asset}.sig").write_text(_minisign(f"signature of {target.asset}", key, 64))
    return tmp_path


def test_lists_every_installer_kind_under_its_platform_key(tmp_path):
    manifest = build_manifest(_release(tmp_path), "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)
    assert set(manifest["platforms"]) == {
        "linux-x86_64-appimage",
        "linux-x86_64-deb",
        "windows-x86_64-nsis",
        "darwin-aarch64-app",
    }


def test_points_each_entry_at_the_tags_own_download_with_its_signature(tmp_path):
    release = _release(tmp_path)
    manifest = build_manifest(release, "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)
    assert manifest["platforms"]["linux-x86_64-deb"] == {
        "url": "https://github.com/schrodlm/rentczecher/releases/download/v0.3.0/rentczecher-linux-amd64.deb",
        "signature": (release / "rentczecher-linux-amd64.deb.sig").read_text(),
    }


def test_states_the_version_without_the_tags_v_and_the_publish_time_in_rfc_3339(tmp_path):
    manifest = build_manifest(_release(tmp_path), "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)
    assert manifest["version"] == "0.3.0"
    assert manifest["pub_date"] == "2026-10-26T17:30:00+00:00"


def test_refuses_a_release_missing_a_signature(tmp_path):
    release = _release(tmp_path)
    (release / "rentczecher-macos-arm64.app.tar.gz.sig").unlink()
    with pytest.raises(ManifestError, match="app.tar.gz.sig is missing"):
        build_manifest(release, "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)


def test_refuses_a_release_missing_an_installer(tmp_path):
    release = _release(tmp_path)
    (release / "rentczecher-windows-x64-setup.exe").unlink()
    with pytest.raises(ManifestError, match="setup.exe is missing"):
        build_manifest(release, "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)


def test_refuses_a_release_signed_with_another_key_than_the_app_trusts(tmp_path):
    with pytest.raises(ManifestError, match="signed with another key"):
        build_manifest(_release(tmp_path, key=OTHER_KEY), "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)


def test_refuses_a_signature_that_is_not_minisign(tmp_path):
    release = _release(tmp_path)
    (release / "rentczecher-linux-amd64.deb.sig").write_text("not base64 at all!")
    with pytest.raises(ManifestError, match="not a minisign key or signature"):
        build_manifest(release, "v0.3.0", REPO, PUBLISHED, PUBLIC_KEY)


def test_refuses_a_tag_that_is_not_a_version(tmp_path):
    with pytest.raises(ManifestError, match="starts with v"):
        build_manifest(_release(tmp_path), "0.3.0", REPO, PUBLISHED, PUBLIC_KEY)


def test_reads_the_key_id_of_the_key_the_app_trusts():
    public_key = json.loads(TAURI_CONFIG.read_text())["plugins"]["updater"]["pubkey"]
    assert key_id(public_key).hex().upper() == "DF5AAFF310C6A18A"
