from fastapi import APIRouter, Request

from rentczecher.adapters.api.models import ProfileModel

router = APIRouter()


@router.get("/v1/profiles", response_model=list[ProfileModel])
def list_profiles(request: Request) -> list[ProfileModel]:
    deps = request.app.state.api_deps
    return [
        ProfileModel.from_config(profile_id, profile)
        for profile_id, profile in deps.config.get("profiles", {}).items()
    ]
