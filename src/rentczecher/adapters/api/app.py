"""FastAPI app factory for the sidecar: wires the auth dependency, the
run manager, and every route onto one app instance.

Every route requires the bearer token from day one, since binding to
loopback does not itself make the port trusted. The token is enforced as a
router-wide dependency rather than per-route so a new route can never ship
unauthenticated by omission. FastAPI's own docs/schema routes are generated
outside that per-router loop, so they are disabled outright rather than left
reachable without the token.
"""

from fastapi import Depends, FastAPI

from rentczecher.adapters.api.auth import BearerAuth
from rentczecher.adapters.api.deps import ApiDeps
from rentczecher.adapters.api.events import EventBroker
from rentczecher.adapters.api.routes import health, listings, profiles, runs
from rentczecher.adapters.api.run_manager import PipelineRunner, RunManager
from rentczecher.services.pipeline import run_profile as default_run_profile


def create_app(
    token: str,
    api_deps: ApiDeps,
    *,
    run_profile: PipelineRunner = default_run_profile,
) -> FastAPI:
    app = FastAPI(
        title="rentczecher sidecar API", version="0",
        docs_url=None, redoc_url=None, openapi_url=None,
    )

    auth = BearerAuth(token)
    app.state.api_deps = api_deps
    app.state.event_broker = EventBroker()
    app.state.run_manager = RunManager(
        api_deps.build_pipeline_deps, app.state.event_broker, run_profile=run_profile)

    for router in (profiles.router, listings.router, runs.router, health.router):
        app.include_router(router, dependencies=[Depends(auth)])

    return app
