from fastapi import APIRouter, Request

from rentczecher_engine.adapters.api.models import ProfileModel

router = APIRouter()


@router.get("/v1/profiles", response_model=list[ProfileModel])
def list_profiles(request: Request) -> list[ProfileModel]:
    deps = request.app.state.api_deps
    return [ProfileModel.from_profile(profile) for profile in deps.profiles]
