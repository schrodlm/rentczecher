from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from rentczecher_engine.adapters.api.deps import resolve_profile
from rentczecher_engine.adapters.api.models import TrackedPropertyModel, PostingPricesModel
from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.domain.listing import TrackedProperty
from rentczecher_engine.domain.location import Location
from rentczecher_engine.domain.profile import Profile

router = APIRouter()


@router.get("/v1/profiles/{profile_id}/properties", response_model=list[TrackedPropertyModel])
def list_tracked_properties(
    request: Request, filter: Literal["new", "all"] = "new",
    profile: Profile = Depends(resolve_profile),
) -> list[TrackedPropertyModel]:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        tracked_properties = store.tracked_properties(profile.id, only_new=filter == "new")
    with deps.open_gazetteer() as gazetteer:
        return [
            TrackedPropertyModel.from_tracked_property(tracked, _resolved_location(tracked, gazetteer))
            for tracked in tracked_properties
        ]


def _resolved_location(tracked: TrackedProperty, gazetteer: Gazetteer) -> Location | None:
    if tracked.property_location is None:
        return None
    return gazetteer.named(tracked.property_location)


@router.get(
    "/v1/profiles/{profile_id}/properties/{property_id}/price-history",
    response_model=list[PostingPricesModel],
)
def price_history(
    property_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> list[PostingPricesModel]:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        postings = store.price_histories(profile.id, property_id)
    if postings is None:
        raise HTTPException(status_code=404, detail=f"profile {profile.id} does not track property {property_id}")
    return [PostingPricesModel.from_posting(posting) for posting in postings]


@router.patch("/v1/profiles/{profile_id}/properties/{property_id}/viewed", status_code=204)
def mark_viewed(
    property_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.mark_viewed(profile.id, property_id)


@router.put("/v1/profiles/{profile_id}/properties/{property_id}/favourite", status_code=204)
def mark_favourite(
    property_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.mark_favourite(profile.id, property_id)


@router.delete("/v1/profiles/{profile_id}/properties/{property_id}/favourite", status_code=204)
def clear_favourite(
    property_id: str, request: Request, profile: Profile = Depends(resolve_profile),
) -> None:
    deps = request.app.state.api_deps
    with deps.open_run_store() as store:
        store.clear_favourite(profile.id, property_id)
