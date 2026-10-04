"""Tests for data path resolution.

Run: python3 -m pytest tests/test_paths.py -v
"""

from rentczecher_engine.adapters.config import paths


def _isolate(monkeypatch, tmp_path):
    """Point every resolution source at tmp_path so no real machine state
    leaks into the test."""
    xdg_data = tmp_path / "xdg-data"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("RENTCZECHER_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path / "repo")
    return xdg_data


def _seed_repo_database(tmp_path):
    repo_data = tmp_path / "repo" / "data"
    repo_data.mkdir(parents=True)
    (repo_data / "rentczecher.db").touch()
    return repo_data


class TestEnvOverride:
    def test_data_override_wins(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "explicit" / "data"))
        assert paths.data_dir() == tmp_path / "explicit" / "data"

    def test_data_override_wins_over_repo_data(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        _seed_repo_database(tmp_path)
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", str(tmp_path / "explicit"))
        assert paths.data_dir() == tmp_path / "explicit"

    def test_empty_string_env_vars_are_ignored(self, monkeypatch, tmp_path):
        xdg_data = _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("RENTCZECHER_DATA_DIR", "")
        assert paths.data_dir() == xdg_data / "rentczecher"

    def test_relative_xdg_dirs_are_ignored_per_spec(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", "also/relative")
        home = tmp_path / "home"
        assert paths.data_dir() == home / ".local" / "share" / "rentczecher"


class TestXdgTier:
    def test_fresh_machine_defaults_to_xdg(self, monkeypatch, tmp_path):
        xdg_data = _isolate(monkeypatch, tmp_path)
        assert paths.data_dir() == xdg_data / "rentczecher"


class TestRepoLocalTier:
    """The repository's data/ is used once it holds a database, so a leftover
    or empty folder never takes over from the XDG data home."""

    def test_repo_data_holding_a_database_is_used(self, monkeypatch, tmp_path):
        _isolate(monkeypatch, tmp_path)
        repo_data = _seed_repo_database(tmp_path)
        assert paths.data_dir() == repo_data

    def test_repo_data_without_a_database_falls_through_to_xdg(self, monkeypatch, tmp_path):
        xdg_data = _isolate(monkeypatch, tmp_path)
        (tmp_path / "repo" / "data").mkdir(parents=True)
        assert paths.data_dir() == xdg_data / "rentczecher"


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
