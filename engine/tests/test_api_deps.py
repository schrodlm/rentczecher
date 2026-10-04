import pytest
from fastapi import HTTPException

from rentczecher_engine.adapters.api.deps import ApiDeps, require_profile
from tests.profiles import profile

MATEJ = profile(id="matej", name="Matěj")


def _deps(tmp_path) -> ApiDeps:
    return ApiDeps(profiles=(MATEJ,), db_path=tmp_path / "db.sqlite", scrapers={})


class TestProfile:
    def test_returns_the_profile_with_that_id(self, tmp_path):
        """profile returns the profile whose id matches."""
        deps = _deps(tmp_path)
        assert deps.profile("matej") == MATEJ

    def test_unknown_profile_is_none(self, tmp_path):
        """An id matching no profile resolves to None, not an error."""
        assert _deps(tmp_path).profile("ghost") is None


class TestRequireProfile:
    def test_returns_the_known_profile(self, tmp_path):
        """A known id resolves to its profile."""
        assert require_profile(_deps(tmp_path), "matej").id == "matej"

    def test_unknown_profile_raises_404(self, tmp_path):
        """An unknown id raises the 404 routes rely on."""
        with pytest.raises(HTTPException) as excinfo:
            require_profile(_deps(tmp_path), "ghost")
        assert excinfo.value.status_code == 404
