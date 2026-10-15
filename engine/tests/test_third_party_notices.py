from importlib import metadata
from pathlib import Path

import pytest

from scripts import third_party_notices
from scripts.third_party_notices import (
    EnginePackages,
    LicenseAllowlist,
    Notice,
    NoticesError,
    PanelPackages,
    ShellCrates,
    render,
)

ALLOWLIST = LicenseAllowlist(frozenset({"MIT", "Apache-2.0", "Unicode-3.0"}))


def _notice(license: str) -> Notice:
    return Notice(name="package", version="1.0.0", license=license, text="license text")


def _distribution(tmp_path: Path, metadata_lines: list[str]) -> metadata.Distribution:
    dist_info = tmp_path / "package-1.0.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("\n".join(["Metadata-Version: 2.4", *metadata_lines]) + "\n")
    return metadata.PathDistribution(dist_info)


def _license_list(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "license.md"
    path.write_text(content, encoding="utf-8")
    return path


class TestLicenseAllowlist:
    @pytest.mark.parametrize("license", ["MIT", "(MIT)", "Apache-2.0 OR GPL-2.0-only", "MIT AND Unicode-3.0"])
    def test_accepts_a_license_the_list_covers(self, license):
        """A single accepted license, either choice of an OR, or every part of
        an AND passes, with or without surrounding parentheses."""
        ALLOWLIST.check([_notice(license)])

    @pytest.mark.parametrize("license", ["GPL-2.0-only", "BSD-2-Clause OR GPL-2.0-only", "MIT AND GPL-2.0-only"])
    def test_rejects_a_license_the_list_does_not_cover(self, license):
        with pytest.raises(NoticesError, match="does not accept"):
            ALLOWLIST.check([_notice(license)])

    @pytest.mark.parametrize("license", ["MIT OR Apache-2.0 AND Unicode-3.0", "(MIT OR Apache-2.0) AND Unicode-3.0"])
    def test_refuses_an_expression_it_cannot_judge(self, license):
        with pytest.raises(NoticesError, match="too complex"):
            ALLOWLIST.check([_notice(license)])

    def test_reads_the_accepted_list_from_the_about_config(self, tmp_path):
        config = tmp_path / "about.toml"
        config.write_text('accepted = ["Zlib"]\n')
        allowlist = LicenseAllowlist.from_about_config(config)
        allowlist.check([_notice("Zlib")])
        with pytest.raises(NoticesError):
            allowlist.check([_notice("MIT")])


class TestEnginePackages:
    def test_lists_the_interpreter_first_and_then_the_runtime_dependencies(self):
        notices = EnginePackages("rentczecher_engine").notices()
        assert notices[0].name == "Python"
        assert notices[0].license == "PSF-2.0"
        names = {notice.name for notice in notices}
        assert {"fastapi", "httpcore", "h11"} <= names

    def test_leaves_out_the_dev_tools(self):
        """Only what the engine requires at runtime is listed, not the dev
        group installed beside it."""
        names = {notice.name.lower() for notice in EnginePackages("rentczecher_engine").notices()}
        assert names.isdisjoint({"pytest", "mypy", "ruff", "pyinstaller"})

    def test_every_listed_package_carries_its_license_text(self):
        for notice in EnginePackages("rentczecher_engine").notices():
            assert notice.text.strip(), notice.name

    def test_prefers_the_spdx_expression(self, tmp_path):
        distribution = _distribution(tmp_path, ["Name: package", "License-Expression: MIT", "License: something else"])
        assert EnginePackages._license_of(distribution) == "MIT"

    def test_translates_a_known_legacy_license_name(self, tmp_path):
        distribution = _distribution(tmp_path, ["Name: package", "License: MIT License"])
        assert EnginePackages._license_of(distribution) == "MIT"

    def test_takes_the_override_for_a_package_naming_no_license(self, tmp_path):
        distribution = _distribution(tmp_path, ["Name: colorama"])
        assert EnginePackages._license_of(distribution) == "BSD-3-Clause"

    @pytest.mark.parametrize("license_line", ["License: BSD License", "Summary: no license field"])
    def test_refuses_a_license_name_it_does_not_know(self, tmp_path, license_line):
        distribution = _distribution(tmp_path, ["Name: package", license_line])
        with pytest.raises(NoticesError, match="LEGACY_LICENSE_NAMES"):
            EnginePackages._license_of(distribution)


class TestPanelPackages:
    def test_reads_each_package_from_the_vite_license_list(self, tmp_path):
        path = _license_list(tmp_path, (
            "# Licenses\n\nThe app bundles dependencies which contain the following licenses:\n\n"
            "## svelte - 5.57.1 (MIT)\n\nMIT text\n\n"
            "## @tauri-apps/api - 2.12.0 (Apache-2.0 OR MIT)\n\nApache text\n"
        ))
        assert PanelPackages(path).notices() == [
            Notice(name="svelte", version="5.57.1", license="MIT", text="MIT text"),
            Notice(name="@tauri-apps/api", version="2.12.0", license="Apache-2.0 OR MIT", text="Apache text"),
        ]

    def test_refuses_a_package_declaring_no_license(self, tmp_path):
        path = _license_list(tmp_path, "## svelte - 5.57.1 (MIT)\n\nMIT text\n\n## odd - 1.0.0\n\nsome text\n")
        with pytest.raises(NoticesError, match="odd 1.0.0 declares no license"):
            PanelPackages(path).notices()

    def test_refuses_a_package_shipping_no_license_text(self, tmp_path):
        path = _license_list(tmp_path, "## bare - 1.0.0 (MIT)\n\n## svelte - 5.57.1 (MIT)\n\nMIT text\n")
        with pytest.raises(NoticesError, match="bare 1.0.0 ships no license text"):
            PanelPackages(path).notices()

    def test_asks_for_the_panel_build_when_the_list_is_missing(self, tmp_path):
        with pytest.raises(NoticesError, match="run the panel's production build first"):
            PanelPackages(tmp_path / "license.md").notices()


class TestShellCrates:
    def test_names_the_install_command_when_cargo_about_is_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(third_party_notices.shutil, "which", lambda _: None)
        with pytest.raises(NoticesError, match="cargo install --locked --features cli cargo-about"):
            ShellCrates(tmp_path, tmp_path / "about.hbs").listing()


class TestRender:
    def test_lays_out_the_three_sections_and_the_built_in_libraries(self):
        text = render(
            engine=[Notice(name="Python", version="3.12.13", license="PSF-2.0", text="PSF text")],
            panel=[Notice(name="svelte", version="5.57.1", license="MIT", text="MIT text")],
            shell="crate listing",
        )
        sections = ["Engine: Python and its packages", "Panel: npm packages", "Shell: Rust crates"]
        positions = [text.index(section) for section in sections]
        assert positions == sorted(positions)
        assert "Python 3.12.13\nLicense: PSF-2.0\n\nPSF text" in text
        assert "OpenSSL" in text
        assert text.rstrip().endswith("crate listing")
