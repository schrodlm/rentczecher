from fastapi import APIRouter, Request
from pydantic import BaseModel

from rentczecher.adapters.api.deps import require_profile
from rentczecher.adapters.api.models import RunTriggeredModel

router = APIRouter()


class TriggerRunBody(BaseModel):
    profile_id: str


@router.post("/v1/runs", response_model=RunTriggeredModel, status_code=202)
def trigger_run(request: Request, body: TriggerRunBody) -> RunTriggeredModel:
    deps = request.app.state.api_deps
    run_manager = request.app.state.run_manager

    profile = require_profile(deps, body.profile_id)

    run_id = run_manager.trigger(body.profile_id, profile)
    return RunTriggeredModel(run_id=run_id, profile_id=body.profile_id)
