"""FastAPI app factory for the sidecar: wires the auth dependency, the
run manager, and every route onto one app instance.

Every route requires the bearer token from day one, since binding to
loopback does not itself make the port trusted. The token is enforced as a
router-wide dependency rather than per-route so a new route can never ship
unauthenticated by omission. FastAPI's own docs/schema routes are generated
outside that per-router loop, so they are disabled outright rather than left
reachable without the token.
"""

from collections.abc import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rentczecher_engine.adapters.api.auth import BearerAuth, BearerOrQueryTokenAuth
from rentczecher_engine.adapters.api.deps import ApiDeps
from rentczecher_engine.adapters.api.events import EventBroker
from rentczecher_engine.adapters.api.routes import events, health, listings, profiles, runs, shutdown
from rentczecher_engine.adapters.api.run_manager import PipelineRunner, RunManager
from rentczecher_engine.domain.errors import ProfileNotFoundError
from rentczecher_engine.services.pipeline import run_profile as default_run_profile


def create_app(
    token: str,
    api_deps: ApiDeps,
    *,
    run_profile: PipelineRunner = default_run_profile,
    allowed_origins: list[str] | None = None,
    request_shutdown: Callable[[], None] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="rentczecher sidecar API", version="0",
        docs_url=None, redoc_url=None, openapi_url=None,
    )

    if allowed_origins:
        # A browser page on another origin (the Vite dev server, the shell's
        # webview) is blocked by the browser's same-origin policy unless the
        # API answers its CORS preflight. Origins are granted explicitly by
        # whoever spawns the sidecar, never by default.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["Authorization"],
        )

    app.add_exception_handler(ProfileNotFoundError, _not_found)

    auth = BearerAuth(token)
    events_auth = BearerOrQueryTokenAuth(token)
    app.state.api_deps = api_deps
    app.state.event_broker = EventBroker()
    app.state.run_manager = RunManager(
        api_deps.build_pipeline_deps, app.state.event_broker, run_profile=run_profile)

    for router in (profiles.router, listings.router, runs.router, health.router):
        app.include_router(router, dependencies=[Depends(auth)])
    app.include_router(events.router, dependencies=[Depends(events_auth)])

    # Only a spawner that can actually stop the process gets a shutdown route.
    if request_shutdown is not None:
        app.state.request_shutdown = request_shutdown
        app.include_router(shutdown.router, dependencies=[Depends(auth)])

    return app


def _not_found(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})
