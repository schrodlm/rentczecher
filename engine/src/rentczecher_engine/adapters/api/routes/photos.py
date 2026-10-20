from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from rentczecher_engine.adapters.photos.store import MEDIA_TYPES, media_type_of

router = APIRouter()

# A key names its file for good, so the webview may keep a photo for as long
# as the link lasts.
_CACHE_CONTROL = "private, max-age=31536000, immutable"


@router.get(
    "/v1/photos/{file_key}",
    response_class=FileResponse,
    responses={200: {"content": {media_type: {} for media_type in MEDIA_TYPES.values()}}},
)
def photo(file_key: str, request: Request) -> FileResponse:
    store = request.app.state.api_deps.photo_store()
    try:
        path = store.path(file_key)
    except ValueError:
        raise HTTPException(status_code=404, detail="no such photo") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="no such photo")
    return FileResponse(path, media_type=media_type_of(file_key), headers={"Cache-Control": _CACHE_CONTROL})
