"""Tests for config/data path resolution.

Run: python3 -m pytest tests/test_paths.py -v
"""

from rentczecher.adapters.config import paths


def _isolate(monkeypatch, tmp_path, repo_has_config=False, xdg_has_config=False):
    """Point every resolution source at tmp_path so no real machine state
    leaks into the test."""
    repo = tmp_path / "repo"
    xdg_config = tmp_path / "xdg-config"
    xdg_data = tmp_path / "xdg-data"
    (repo / "src").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("RENTCZECHER_CONFIG", raising=False)
    monkeypatch.delenv("RENTCZECHER_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
    monkeypatch.setattr(paths, "repo_root", lambda: repo)
    if repo_has_config:
        (repo / "config.yaml").write_text("repo config\n")
    if xdg_has_config:
        (xdg_config / "rentczecher").mkdir(parents=True)
        (xdg_config / "rentczecher" / "config.yaml").write_text("xdg config\n")
    return repo, xdg_config, xdg_data


class TestEnvOverride:
    def test_env_vars_win_over_everything(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path, repo_has_config=True, xdg_has_config=True)
        monkeypatch.setenv("RENTCZECHER_CONFIG", str(tmp_path / "explicit" / "cfg.yaml"))
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "explicit" / "data"))
        assert paths.config_path() == tmp_path / "explicit" / "cfg.yaml"
        assert paths.data_dir() == tmp_path / "explicit" / "data"

    def test_data_override_alone_leaves_config_on_its_tier(self, monkeypatch, tmp_path):
        repo, _, _ = _isolate(monkeypatch, tmp_path, repo_has_config=True)
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "elsewhere"))
        assert paths.config_path() == repo / "config.yaml"
        assert paths.data_dir() == tmp_path / "elsewhere"

    def test_config_override_alone_anchors_data_beside_it(self, monkeypatch, tmp_path):
        """An explicit config must not leave data on an ambient tier - one
        override may never split an installation across two homes."""
        _isolate(monkeypatch, tmp_path, repo_has_config=True, xdg_has_config=True)
        monkeypatch.setenv("RENTCZECHER_CONFIG", str(tmp_path / "mine" / "config.yaml"))
        assert paths.config_path() == tmp_path / "mine" / "config.yaml"
        assert paths.data_dir() == tmp_path / "mine" / "data"

    def test_empty_string_env_vars_are_ignored(self, monkeypatch, tmp_path):
        _, xdg_config, _ = _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("RENTCZECHER_CONFIG", "")
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", "")
        assert paths.config_path() == xdg_config / "rentczecher" / "config.yaml"

    def test_relative_xdg_dirs_are_ignored_per_spec(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", "relative/path")
        monkeypatch.setenv("XDG_DATA_HOME", "also/relative")
        home = tmp_path / "home"
        assert paths.config_path() == home / ".config" / "rentczecher" / "config.yaml"
        assert paths.data_dir() == home / ".local" / "share" / "rentczecher"


class TestXdgTier:
    def test_existing_xdg_config_wins_over_repo_local(self, monkeypatch, tmp_path):
        _, xdg_config, xdg_data = _isolate(
            monkeypatch, tmp_path, repo_has_config=True, xdg_has_config=True
        )
        assert paths.config_path() == xdg_config / "rentczecher" / "config.yaml"
        assert paths.data_dir() == xdg_data / "rentczecher"

    def test_fresh_machine_defaults_to_xdg(self, monkeypatch, tmp_path):
        _, xdg_config, xdg_data = _isolate(monkeypatch, tmp_path)
        assert paths.config_path() == xdg_config / "rentczecher" / "config.yaml"
        assert paths.data_dir() == xdg_data / "rentczecher"


class TestRepoLocalTier:
    def test_repo_local_config_keeps_everything_repo_local(self, monkeypatch, tmp_path):
        repo, _, _ = _isolate(monkeypatch, tmp_path, repo_has_config=True)
        assert paths.config_path() == repo / "config.yaml"
        assert paths.data_dir() == repo / "data"

    def test_data_follows_config_even_when_repo_data_is_missing(self, monkeypatch, tmp_path):
        """A repo-local installation whose data/ was deleted must not silently
        split its state into the XDG data home."""
        repo, _, _ = _isolate(monkeypatch, tmp_path, repo_has_config=True)
        assert not (repo / "data").exists()
        assert paths.data_dir() == repo / "data"


class TestPidLock:
    def test_pid_lock_lives_under_the_resolved_data_dir(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "d"))
        assert paths.pid_lock_path() == tmp_path / "d" / "watchdog.pid"


class TestDbPath:
    def test_db_lives_under_the_resolved_data_dir(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "d"))
        assert paths.db_path() == tmp_path / "d" / "rentczecher.db"
