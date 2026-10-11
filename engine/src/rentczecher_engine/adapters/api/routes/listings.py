from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from rentczecher_engine.adapters.api.deps import resolve_profile
from rentczecher_engine.adapters.api.models import ListingModel, PostingPricesModel
from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.domain.listing import InboxCard
from rentczecher_engine.domain.location import Location
from rentczecher_engine.domain.profile import Profile

router = APIRouter()


@router.get("/v1/profiles/{profile_id}/listings", response_model=list[ListingModel])
def list_listings(
    request: Request, filter: Literal["new", "all"] = "new",
    profile: Profile = Depends(resolve_profile),
) -> list[ListingModel]:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        cards = store.inbox_listings(profile.id, only_new=filter == "new")
    with deps.open_gazetteer() as gazetteer:
        return [ListingModel.from_card(card, _resolved_location(card, gazetteer)) for card in cards]


def _resolved_location(card: InboxCard, gazetteer: Gazetteer) -> Location | None:
    if card.property_location is None:
        return None
    return gazetteer.named(card.property_location)


@router.get(
    "/v1/profiles/{profile_id}/listings/{listing_id}/price-history",
    response_model=list[PostingPricesModel],
)
def price_history(
    listing_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> list[PostingPricesModel]:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        postings = store.price_histories(profile.id, listing_id)
    if postings is None:
        raise HTTPException(status_code=404, detail=f"profile {profile.id} does not track listing {listing_id}")
    return [PostingPricesModel.from_posting(posting) for posting in postings]


@router.patch("/v1/profiles/{profile_id}/listings/{listing_id}/viewed", status_code=204)
def mark_viewed(
    listing_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.mark_viewed(profile.id, listing_id)


@router.put("/v1/profiles/{profile_id}/listings/{listing_id}/favourite", status_code=204)
def mark_favourite(
    listing_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.mark_favourite(profile.id, listing_id)


@router.delete("/v1/profiles/{profile_id}/listings/{listing_id}/favourite", status_code=204)
def clear_favourite(
    listing_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.clear_favourite(profile.id, listing_id)
