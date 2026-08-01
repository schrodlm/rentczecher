"""Tests for the installer's pure logic (crontab merging, config init).

Run: python3 -m pytest tests/test_install.py -v
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "install", Path(__file__).parent.parent / "install.py"
)
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)


FOREIGN_ENTRIES = (
    "MAILTO=someone@example.com\n"
    "*/5 * * * * /usr/local/bin/backup.sh\n"
    "# a comment the user wrote\n"
    "0 4 * * 1 certbot renew"
)


class TestMergeCrontab:
    """Foreign crontab content survives byte-identical; exactly one managed
    rentczecher block exists afterwards; legacy entries are removed."""

    def test_empty_crontab_gets_exactly_the_managed_block(self):
        merged = install.merge_crontab("", interval_hours=3)
        assert merged == install.render_cron_block(3) + "\n"

    def test_foreign_entries_are_preserved_verbatim(self):
        merged = install.merge_crontab(FOREIGN_ENTRIES, interval_hours=3)
        assert merged.startswith(FOREIGN_ENTRIES)
        assert install.CRON_BLOCK_BEGIN in merged
        assert install.CRON_BLOCK_END in merged

    def test_rerun_is_idempotent(self):
        once = install.merge_crontab(FOREIGN_ENTRIES, interval_hours=3)
        twice = install.merge_crontab(once, interval_hours=3)
        assert once == twice

    def test_rerun_replaces_block_when_interval_changes(self):
        once = install.merge_crontab(FOREIGN_ENTRIES, interval_hours=3)
        changed = install.merge_crontab(once, interval_hours=6)
        assert "0 */6 * * *" in changed
        assert "0 */3 * * *" not in changed
        assert changed.count(install.CRON_BLOCK_BEGIN) == 1

    def test_legacy_main_py_entry_is_removed(self):
        legacy = (
            f"0 */3 * * * {install.REPO_ROOT}/venv/bin/python "
            f"{install.REPO_ROOT}/main.py >> {install.REPO_ROOT}/data/cron.log 2>&1"
        )
        merged = install.merge_crontab(FOREIGN_ENTRIES + "\n" + legacy, interval_hours=3)
        assert "main.py" not in merged
        assert merged.startswith(FOREIGN_ENTRIES)

    def test_managed_entry_uses_absolute_paths(self):
        block = install.render_cron_block(3)
        entry = block.splitlines()[1]
        assert str(install.ENTRY_POINT) in entry
        assert str(install.CRON_LOG) in entry
        assert entry.startswith("0 */3 * * * /")


class TestStripHelpers:
    def test_strip_managed_block_leaves_foreign_lines(self):
        text = FOREIGN_ENTRIES + "\n" + install.render_cron_block(3)
        assert install.strip_managed_block(text) == FOREIGN_ENTRIES

    def test_strip_managed_block_without_block_is_identity(self):
        assert install.strip_managed_block(FOREIGN_ENTRIES) == FOREIGN_ENTRIES

    def test_unterminated_block_is_refused_not_swallowed(self):
        import pytest
        corrupted = (
            FOREIGN_ENTRIES + "\n" + install.CRON_BLOCK_BEGIN
            + "\n0 */3 * * * /old/entry\n0 4 * * 1 certbot renew"
        )
        with pytest.raises(ValueError, match="end marker"):
            install.strip_managed_block(corrupted)
        with pytest.raises(ValueError, match="end marker"):
            install.merge_crontab(corrupted, interval_hours=3)

    def test_interval_24_renders_a_plain_daily_schedule(self):
        block = install.render_cron_block(24)
        assert "0 0 * * *" in block
        assert "*/24" not in block

    def test_strip_legacy_only_matches_this_repos_main_py(self):
        other = "0 * * * * /somewhere/else/main.py"
        assert install.strip_legacy_entries(other) == other


class TestLookalikeEntries:
    """Cron lines from other checkouts of this project are reported, never
    silently removed or silently kept."""

    def test_old_checkout_under_different_directory_is_flagged(self):
        line = "0 */3 * * * /home/x/dev/byt_watchdog/venv/bin/python /home/x/dev/byt_watchdog/main.py"
        assert install.lookalike_entries(FOREIGN_ENTRIES + "\n" + line) == [line]

    def test_foreign_and_comment_lines_are_not_flagged(self):
        text = FOREIGN_ENTRIES + "\n# rentczecher was here once"
        assert install.lookalike_entries(text) == []


class TestEnsureConfig:
    def test_existing_config_is_never_overwritten(self, tmp_path, monkeypatch, capsys):
        config = tmp_path / "config.yaml"
        config.write_text("my precious settings\n")
        monkeypatch.setattr(install, "CONFIG", config)
        monkeypatch.setattr(install, "CONFIG_EXAMPLE", tmp_path / "config.example.yaml")
        assert install.ensure_config(dry_run=False) == "kept"
        assert config.read_text() == "my precious settings\n"

    def test_config_created_from_example_when_absent(self, tmp_path, monkeypatch):
        example = tmp_path / "config.example.yaml"
        example.write_text("template\n")
        config = tmp_path / "config.yaml"
        monkeypatch.setattr(install, "CONFIG", config)
        monkeypatch.setattr(install, "CONFIG_EXAMPLE", example)
        assert install.ensure_config(dry_run=False) == "created"
        assert config.read_text() == "template\n"

    def test_missing_parent_directories_are_created(self, tmp_path, monkeypatch):
        """XDG config homes do not exist on a fresh machine."""
        example = tmp_path / "config.example.yaml"
        example.write_text("template\n")
        config = tmp_path / "deep" / "nested" / "config.yaml"
        monkeypatch.setattr(install, "CONFIG", config)
        monkeypatch.setattr(install, "CONFIG_EXAMPLE", example)
        assert install.ensure_config(dry_run=False) == "created"
        assert config.read_text() == "template\n"

    def test_dry_run_creates_nothing(self, tmp_path, monkeypatch):
        example = tmp_path / "config.example.yaml"
        example.write_text("template\n")
        config = tmp_path / "config.yaml"
        monkeypatch.setattr(install, "CONFIG", config)
        monkeypatch.setattr(install, "CONFIG_EXAMPLE", example)
        assert install.ensure_config(dry_run=True) == "created"
        assert not config.exists()


class TestNextSteps:
    """A dry run must never point the user at commands that need artifacts
    the dry run did not create."""

    def test_dry_run_epilogue_suggests_real_install_only(self, capsys):
        install.print_next_steps("created", dry_run=True)
        out = capsys.readouterr().out
        assert "./install.py" in out
        assert "--dry-run" not in out.replace("nothing was changed", "")

    def test_fresh_config_epilogue_says_edit_config_first(self, capsys):
        install.print_next_steps("created", dry_run=False)
        out = capsys.readouterr().out
        assert "1) edit" in out
        assert str(install.CONFIG) in out
        assert "2) test it" in out

    def test_kept_config_epilogue_goes_straight_to_testing(self, capsys):
        install.print_next_steps("kept", dry_run=False)
        out = capsys.readouterr().out
        assert "edit" not in out
        assert "test it" in out


class TestResolverWiring:
    def test_install_constants_come_from_the_shared_resolver(self):
        from rentczecher.adapters.config import paths
        assert install.CONFIG == paths.config_path()
        assert install.DATA_DIR == paths.data_dir()


class TestOrphanWarning:
    def test_warns_when_install_targets_a_different_data_home(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-x.json").write_text("{}")
        monkeypatch.setattr(install, "repo_root", lambda: repo)
        monkeypatch.setattr(install, "DATA_DIR", tmp_path / "xdg" / "rentczecher")
        install.warn_if_repo_data_orphaned()
        assert "WARNING" in capsys.readouterr().out

    def test_silent_when_install_stays_repo_local(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path / "repo"
        (repo / "data").mkdir(parents=True)
        (repo / "data" / "seen-x.json").write_text("{}")
        monkeypatch.setattr(install, "repo_root", lambda: repo)
        monkeypatch.setattr(install, "DATA_DIR", repo / "data")
        install.warn_if_repo_data_orphaned()
        assert "WARNING" not in capsys.readouterr().out


class TestParseArgs:
    def test_defaults(self):
        args = install.parse_args([])
        assert args.interval_hours == 3
        assert not args.no_cron
        assert not args.dry_run

    def test_interval_out_of_range_is_rejected(self):
        import pytest
        with pytest.raises(SystemExit):
            install.parse_args(["--interval-hours", "0"])
        with pytest.raises(SystemExit):
            install.parse_args(["--interval-hours", "25"])
