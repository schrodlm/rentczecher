from contextlib import closing
from pathlib import Path

import pytest
from fastapi import HTTPException

from rentczecher_engine.adapters.api.deps import ApiDeps, require_profile
from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.domain.profile import Profile
from tests.profiles import stored_profile


def _db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db.sqlite"
    with closing(connection.connect(db_path)) as conn:
        migrate.apply_pending(conn)
    return db_path


def _deps(tmp_path: Path) -> ApiDeps:
    return ApiDeps(db_path=_db(tmp_path), scrapers={})


@pytest.fixture
def matej(tmp_path) -> Profile:
    """A profile stored in the database the test's deps read."""
    with closing(connection.connect(_db(tmp_path))) as conn:
        return stored_profile(conn, name="Matěj")


class TestProfile:
    def test_returns_the_profile_with_that_id(self, tmp_path, matej):
        """profile returns the profile whose id matches."""
        assert _deps(tmp_path).profile(matej.id) == matej

    def test_unknown_profile_is_none(self, tmp_path, matej):
        """An id matching no profile resolves to None, not an error."""
        assert _deps(tmp_path).profile("ghost") is None


class TestRequireProfile:
    def test_returns_the_known_profile(self, tmp_path, matej):
        """A known id resolves to its profile."""
        assert require_profile(_deps(tmp_path), matej.id).id == matej.id

    def test_unknown_profile_raises_404(self, tmp_path, matej):
        """An unknown id raises the 404 routes rely on."""
        with pytest.raises(HTTPException) as excinfo:
            require_profile(_deps(tmp_path), "ghost")
        assert excinfo.value.status_code == 404
