import pytest
from fastapi import HTTPException

from rentczecher.adapters.api.auth import BearerAuth, BearerOrQueryTokenAuth


def _rejects(auth, **kwargs) -> None:
    with pytest.raises(HTTPException) as excinfo:
        auth(**kwargs)
    assert excinfo.value.status_code == 401


class TestBearerAuth:
    def test_accepts_the_bound_token(self):
        """A well-formed Authorization header carrying the bound token passes."""
        BearerAuth("secret")(authorization="Bearer secret")

    def test_rejects_a_missing_header(self):
        """A request without an Authorization header is rejected with 401."""
        _rejects(BearerAuth("secret"), authorization=None)

    def test_rejects_a_wrong_token(self):
        """A well-formed header presenting a different token is rejected with 401."""
        _rejects(BearerAuth("secret"), authorization="Bearer wrong")

    def test_rejects_a_non_bearer_scheme(self):
        """An Authorization header without the Bearer scheme is rejected with 401."""
        _rejects(BearerAuth("secret"), authorization="Basic secret")


class TestBearerOrQueryTokenAuth:
    def test_accepts_the_bound_token_in_the_header(self):
        """The header path works exactly as on BearerAuth."""
        BearerOrQueryTokenAuth("secret")(authorization="Bearer secret", token=None)

    def test_accepts_the_bound_token_as_query_parameter(self):
        """With no Authorization header, a ?token= carrying the bound token passes."""
        BearerOrQueryTokenAuth("secret")(authorization=None, token="secret")

    def test_header_takes_precedence_over_query(self):
        """A well-formed header is judged on its own; the query token cannot rescue it."""
        _rejects(BearerOrQueryTokenAuth("secret"), authorization="Bearer wrong", token="secret")

    def test_rejects_a_wrong_query_token(self):
        """A ?token= presenting a different token is rejected with 401."""
        _rejects(BearerOrQueryTokenAuth("secret"), authorization=None, token="wrong")

    def test_rejects_when_both_are_missing(self):
        """No header and no query token is rejected with 401."""
        _rejects(BearerOrQueryTokenAuth("secret"), authorization=None, token=None)
