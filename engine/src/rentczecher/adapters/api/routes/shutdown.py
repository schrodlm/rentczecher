from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/v1/shutdown", status_code=202)
def shutdown(request: Request) -> None:
    request.app.state.request_shutdown()
