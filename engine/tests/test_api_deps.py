import pytest
from fastapi import HTTPException

from rentczecher.adapters.api.deps import ApiDeps, require_profile

CONFIG = {"profiles": {"matej": {"name": "Matěj", "to": []}}}


def _deps(tmp_path) -> ApiDeps:
    return ApiDeps(config=CONFIG, db_path=tmp_path / "db.sqlite", scrapers={})


class TestProfileConfig:
    def test_returns_the_profile_with_its_id_folded_in(self, tmp_path):
        """profile_config returns the config entry with the profile id added."""
        deps = _deps(tmp_path)
        assert deps.profile_config("matej") == {"name": "Matěj", "to": [], "id": "matej"}

    def test_unknown_profile_is_none(self, tmp_path):
        """An id absent from the config resolves to None, not an error."""
        assert _deps(tmp_path).profile_config("ghost") is None


class TestRequireProfile:
    def test_returns_the_known_profile(self, tmp_path):
        """A known id passes through with its config."""
        assert require_profile(_deps(tmp_path), "matej")["id"] == "matej"

    def test_unknown_profile_raises_404(self, tmp_path):
        """An unknown id raises the 404 routes rely on."""
        with pytest.raises(HTTPException) as excinfo:
            require_profile(_deps(tmp_path), "ghost")
        assert excinfo.value.status_code == 404
