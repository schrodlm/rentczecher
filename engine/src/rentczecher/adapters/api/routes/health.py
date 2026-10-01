from fastapi import APIRouter, Request

from rentczecher.adapters.api.models import PortalHealthModel

router = APIRouter()


@router.get("/v1/health", response_model=list[PortalHealthModel])
def health(request: Request) -> list[PortalHealthModel]:
    run_manager = request.app.state.run_manager
    return [
        PortalHealthModel.from_entry(portal, entry)
        for portal, entry in sorted(run_manager.last_health().items())
    ]
