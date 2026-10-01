from typing import Literal

from fastapi import APIRouter, Depends, Request

from rentczecher.adapters.api.deps import resolve_profile
from rentczecher.adapters.api.models import ListingModel

router = APIRouter()


@router.get("/v1/profiles/{profile_id}/listings", response_model=list[ListingModel])
def list_listings(
    profile_id: str, request: Request, filter: Literal["new", "all"] = "new",
    profile: dict = Depends(resolve_profile),
) -> list[ListingModel]:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        cards = store.inbox_listings(profile_id, only_new=filter == "new")
    return [ListingModel.from_card(card) for card in cards]


@router.patch("/v1/profiles/{profile_id}/listings/{listing_id}/viewed", status_code=204)
def mark_viewed(
    profile_id: str, listing_id: str, request: Request, profile: dict = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.mark_viewed(profile_id, listing_id)
