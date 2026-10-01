"""Bearer-token auth: every request must carry the token the shell handed
the sidecar at spawn. The loopback bind is not itself trusted."""

import logging

from fastapi import Header, HTTPException

log = logging.getLogger("rentczecher.api")


class BearerAuth:
    """A FastAPI dependency bound to one process's token, so each app
    instance (real or test) checks against its own value rather than a
    process-wide global."""

    def __init__(self, token: str):
        self._token = token

    def __call__(self, authorization: str | None = Header(default=None)) -> None:
        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        if authorization.removeprefix("Bearer ") != self._token:
            raise HTTPException(status_code=401, detail="invalid bearer token")


class BearerOrQueryTokenAuth(BearerAuth):
    """BearerAuth plus a `?token=` query-parameter fallback, for the SSE
    route alone: the browser-native EventSource API cannot set request
    headers, so that route is the one documented exception to
    "auth is always via header". A distinct class, rather than a flag on
    BearerAuth, keeps the extra query parameter out of every other route's
    generated OpenAPI schema.
    """

    def __call__(
        self,
        authorization: str | None = Header(default=None),
        token: str | None = None,
    ) -> None:
        if authorization is not None and authorization.startswith("Bearer "):
            presented = authorization.removeprefix("Bearer ")
        elif token is not None:
            log.debug("accepted a query-string token in place of the Authorization header")
            presented = token
        else:
            raise HTTPException(status_code=401, detail="missing bearer token")

        if presented != self._token:
            raise HTTPException(status_code=401, detail="invalid bearer token")
