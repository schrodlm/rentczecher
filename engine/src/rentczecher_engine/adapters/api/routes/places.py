from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from rentczecher_engine.adapters.api.deps import ApiDeps
from rentczecher_engine.adapters.api.models import NamedPlaceModel, PlaceRefModel
from rentczecher_engine.domain.location import PlaceKind, PlaceRef

router = APIRouter()


@router.get("/v1/places", response_model=list[NamedPlaceModel])
def search_places(
    request: Request, q: str, within: str | None = None,
    kind: Annotated[list[PlaceKind] | None, Query()] = None,
) -> list[NamedPlaceModel]:
    """Places whose name starts with q, optionally only those at least
    partly inside within, given as <kind>:<code>, and only of the given
    kinds."""
    deps: ApiDeps = request.app.state.api_deps
    within_place = _within_place(within) if within is not None else None
    with deps.open_gazetteer() as gazetteer:
        matches = gazetteer.search_places(q, within_place, tuple(kind) if kind else None)
    return [NamedPlaceModel.from_match(match) for match in matches]


def _within_place(within: str) -> PlaceRef:
    kind, _, code = within.partition(":")
    try:
        place = PlaceRefModel.model_validate({"kind": kind, "code": code})
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=f"within must be <kind>:<code>, not {within!r}") from error
    return place.to_place_ref()
