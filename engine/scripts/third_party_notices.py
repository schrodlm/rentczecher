#!/usr/bin/env python3
"""Writes the third-party notices the installers ship: every package bundled
into the app, with its license text. Run on the OS whose installers are being
built, after the panel's production build.

Run: uv run python scripts/third_party_notices.py
"""

import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ENGINE = Path(__file__).resolve().parent.parent
REPO = ENGINE.parent
SHELL = REPO / "shell"
ABOUT_CONFIG = SHELL / "about.toml"
ABOUT_TEMPLATE = SHELL / "about.hbs"
PANEL_LICENSES = REPO / "panel" / ".svelte-kit" / "output" / "client" / ".vite" / "license.md"
NOTICES = SHELL / "THIRD_PARTY_NOTICES.txt"

ENGINE_DISTRIBUTION = "rentczecher_engine"

# Packages that predate SPDX license expressions name their license in free
# text. Only names known to mean one SPDX license are translated.
LEGACY_LICENSE_NAMES = {
    "MIT": "MIT",
    "MIT License": "MIT",
    "MPL-2.0": "MPL-2.0",
    "BSD-3-Clause": "BSD-3-Clause",
}

# Packages that name no license in their metadata at all, read off their
# license file.
LICENSE_OVERRIDES = {
    "colorama": "BSD-3-Clause",
}

# Libraries compiled into the Python interpreter and into lxml. No package
# metadata names them, so they are credited here by hand.
BUILT_IN_LIBRARIES = """\
The Python interpreter and lxml are built with these libraries:

  OpenSSL          Apache-2.0
  SQLite           public domain
  zlib             Zlib
  libffi           MIT
  XZ Utils         0BSD
  bzip2            bzip2-1.0.6
  mpdecimal        BSD-2-Clause
  Expat            MIT
  libxml2          MIT            (in lxml)
  libxslt          MIT            (in lxml)
  GNU libiconv     LGPL-2.1       (in lxml)
"""

LICENSE_FILE_NAME = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE)", re.IGNORECASE)
PANEL_HEADING = re.compile(r"^## (?P<name>.+?) - (?P<version>\S+)(?: \((?P<license>.+)\))?$", re.MULTILINE)

RULE = "-" * 80
DOUBLE_RULE = "=" * 80


class NoticesError(Exception):
    """A package whose license cannot be shipped or cannot be found."""


@dataclass(frozen=True)
class Notice:
    name: str
    version: str
    license: str
    text: str


class LicenseAllowlist:
    """The licenses shell/about.toml accepts, applied to SPDX expressions of
    one license or of licenses joined by only OR or only AND."""

    def __init__(self, accepted: frozenset[str]) -> None:
        self._accepted = accepted

    @classmethod
    def from_about_config(cls, path: Path) -> "LicenseAllowlist":
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(frozenset(config["accepted"]))

    def _allows(self, expression: str) -> bool:
        bare = expression.strip()
        if bare.startswith("(") and bare.endswith(")"):
            bare = bare[1:-1].strip()
        if "(" in bare or ")" in bare or (" OR " in bare and " AND " in bare):
            raise NoticesError(f"license expression too complex to check: {expression}")
        if " OR " in bare:
            return any(part.strip() in self._accepted for part in bare.split(" OR "))
        return all(part.strip() in self._accepted for part in bare.split(" AND "))

    def check(self, notices: list[Notice]) -> None:
        for notice in notices:
            if not self._allows(notice.license):
                raise NoticesError(
                    f"{notice.name} {notice.version} is licensed {notice.license}, "
                    "which shell/about.toml does not accept"
                )


class EnginePackages:
    """The Python the frozen engine bundles: the interpreter itself and every
    runtime dependency that applies to this interpreter and OS."""

    def __init__(self, root: str) -> None:
        self._root = root

    def notices(self) -> list[Notice]:
        names = sorted(self._runtime_dependencies())
        return [self._interpreter_notice()] + [self._package_notice(name) for name in names]

    def _runtime_dependencies(self) -> set[str]:
        found: set[str] = set()
        pending = [self._root]
        while pending:
            for line in metadata.requires(pending.pop()) or []:
                requirement = Requirement(line)
                if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
                    continue
                name = canonicalize_name(requirement.name)
                if name not in found:
                    found.add(name)
                    pending.append(name)
        return found

    def _interpreter_notice(self) -> Notice:
        # The license sits beside the stdlib on POSIX and at the install prefix on Windows.
        candidates = [Path(sysconfig.get_path("stdlib")) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE.txt"]
        for candidate in candidates:
            if candidate.is_file():
                text = candidate.read_text(encoding="utf-8")
                return Notice(name="Python", version=platform.python_version(), license="PSF-2.0", text=text)
        raise NoticesError(f"the Python interpreter's LICENSE.txt is in none of {candidates}")

    def _package_notice(self, name: str) -> Notice:
        distribution = metadata.distribution(name)
        texts = [
            distribution.locate_file(file).read_text(encoding="utf-8")
            for file in distribution.files or []
            if ".dist-info" in file.parent.as_posix() and LICENSE_FILE_NAME.match(file.name)
        ]
        if not "".join(texts).strip():
            raise NoticesError(f"{name} ships no license text")
        return Notice(
            name=distribution.metadata["Name"],
            version=distribution.version,
            license=self._license_of(distribution),
            text="\n\n".join(texts),
        )

    @staticmethod
    def _license_of(distribution: metadata.Distribution) -> str:
        name = canonicalize_name(distribution.metadata["Name"])
        if name in LICENSE_OVERRIDES:
            return LICENSE_OVERRIDES[name]
        expression = distribution.metadata.get("License-Expression")
        if expression:
            return expression
        legacy_name = distribution.metadata.get("License", "").strip()
        if legacy_name in LEGACY_LICENSE_NAMES:
            return LEGACY_LICENSE_NAMES[legacy_name]
        raise NoticesError(
            f"{distribution.metadata['Name']} names its license as {legacy_name!r}, "
            "add it to LEGACY_LICENSE_NAMES"
        )


class PanelPackages:
    """The npm packages the panel bundles, from the license list Vite writes
    during the panel's production build."""

    def __init__(self, license_list: Path) -> None:
        self._license_list = license_list

    def notices(self) -> list[Notice]:
        if not self._license_list.is_file():
            raise NoticesError(f"{self._license_list} is missing, run the panel's production build first")
        content = self._license_list.read_text(encoding="utf-8")
        headings = list(PANEL_HEADING.finditer(content))
        if not headings:
            raise NoticesError(f"{self._license_list} lists no packages")
        ends = [heading.start() for heading in headings[1:]] + [len(content)]
        notices = [
            Notice(
                name=heading["name"],
                version=heading["version"],
                license=heading["license"] or "",
                text=content[heading.end():end].strip(),
            )
            for heading, end in zip(headings, ends, strict=True)
        ]
        for notice in notices:
            if not notice.license:
                raise NoticesError(f"{notice.name} {notice.version} declares no license in its package.json")
            if not notice.text:
                raise NoticesError(f"{notice.name} {notice.version} ships no license text")
        return notices


class ShellCrates:
    """The Rust crates the shell links, listed by cargo-about, which also
    checks them against shell/about.toml.

    Listing reads each crate's own license files, so it downloads any crate
    not yet in Cargo's local registry, pinned to Cargo.lock. It runs before
    the shell is compiled, since the installer's resources must exist by
    then, and the compile then finds every crate already downloaded."""

    def __init__(self, shell: Path, template: Path) -> None:
        self._shell = shell
        self._template = template

    def listing(self) -> str:
        if shutil.which("cargo-about") is None:
            raise NoticesError("cargo-about is not installed: cargo install --locked --features cli cargo-about")
        # cargo-about refuses to write its listing to stdout under PowerShell.
        with tempfile.TemporaryDirectory() as scratch:
            listing = Path(scratch) / "crates.txt"
            result = subprocess.run(
                ["cargo", "about", "generate", "--locked", "--fail", "-o", str(listing), str(self._template)],
                cwd=self._shell,
                capture_output=True,
                encoding="utf-8",
            )
            if result.returncode != 0:
                raise NoticesError(f"cargo-about failed:\n{result.stderr}")
            return listing.read_text(encoding="utf-8").strip()


def render(engine: list[Notice], panel: list[Notice], shell: str) -> str:
    parts = [
        "rentczecher bundles the following third-party software, each listed",
        "with the license it is distributed under.",
        "",
        _section_title("Engine: Python and its packages"),
        *[_notice_block(notice) for notice in engine],
        RULE,
        BUILT_IN_LIBRARIES,
        _section_title("Panel: npm packages"),
        *[_notice_block(notice) for notice in panel],
        _section_title("Shell: Rust crates"),
        shell,
        "",
    ]
    return "\n".join(parts)


def _section_title(title: str) -> str:
    return f"\n{DOUBLE_RULE}\n{title}\n{DOUBLE_RULE}\n"


def _notice_block(notice: Notice) -> str:
    return f"{RULE}\n{notice.name} {notice.version}\nLicense: {notice.license}\n\n{notice.text.strip()}\n"


def main() -> None:
    allowlist = LicenseAllowlist.from_about_config(ABOUT_CONFIG)
    try:
        engine = EnginePackages(ENGINE_DISTRIBUTION).notices()
        panel = PanelPackages(PANEL_LICENSES).notices()
        allowlist.check(engine + panel)
        shell = ShellCrates(SHELL, ABOUT_TEMPLATE).listing()
    except NoticesError as error:
        sys.exit(f"third-party notices: {error}")
    NOTICES.write_text(render(engine, panel, shell), encoding="utf-8")
    print(f"Wrote {NOTICES}")


if __name__ == "__main__":
    main()
