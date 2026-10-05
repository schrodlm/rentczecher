import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Request

from rentczecher_engine.adapters.api.deps import ApiDeps, resolve_profile
from rentczecher_engine.adapters.api.models import NewProfileBody, ProfileModel, ProfileUpdateBody
from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.domain.errors import PlaceNotFoundError, ProfileNotFoundError
from rentczecher_engine.domain.location import PlaceMatch, PlaceRef
from rentczecher_engine.domain.profile import Profile

router = APIRouter()


@router.get("/v1/profiles", response_model=list[ProfileModel])
def list_profiles(request: Request) -> list[ProfileModel]:
    deps: ApiDeps = request.app.state.api_deps
    profiles = deps.list_profiles()
    with deps.open_gazetteer() as gazetteer:
        return [_profile_model(profile, gazetteer) for profile in profiles]


@router.get("/v1/profiles/{profile_id}", response_model=ProfileModel)
def get_profile(request: Request, profile: Profile = Depends(resolve_profile)) -> ProfileModel:
    deps: ApiDeps = request.app.state.api_deps
    with deps.open_gazetteer() as gazetteer:
        return _profile_model(profile, gazetteer)


@router.post("/v1/profiles", response_model=ProfileModel, status_code=201)
def create_profile(request: Request, body: NewProfileBody) -> ProfileModel:
    deps: ApiDeps = request.app.state.api_deps
    with deps.open_gazetteer() as gazetteer:
        with _unprocessable_when_invalid(), deps.edit_profiles() as profiles:
            criteria = body.criteria.to_criteria()
            preferences = body.preferences.to_preferences()
            _require_known_places(gazetteer, (criteria.place, *preferences.preferred_places))
            profile = profiles.add(body.name, tuple(body.portals), criteria, preferences)
        return _profile_model(profile, gazetteer)


@router.put("/v1/profiles/{profile_id}", response_model=ProfileModel)
def update_profile(
    request: Request, body: ProfileUpdateBody, current: Profile = Depends(resolve_profile),
) -> ProfileModel:
    deps: ApiDeps = request.app.state.api_deps
    with deps.open_gazetteer() as gazetteer:
        with _unprocessable_when_invalid(), deps.edit_profiles() as profiles:
            preferences = body.preferences.to_preferences()
            _require_known_places(gazetteer, preferences.preferred_places)
            profile = profiles.update(current.id, body.name, body.paused, tuple(body.portals), preferences)
        # The profile may have been deleted since it was resolved.
        if profile is None:
            raise ProfileNotFoundError(current.id)
        return _profile_model(profile, gazetteer)


@router.delete("/v1/profiles/{profile_id}", status_code=204)
def delete_profile(request: Request, profile: Profile = Depends(resolve_profile)) -> None:
    deps: ApiDeps = request.app.state.api_deps
    with deps.edit_profiles() as profiles:
        profiles.delete(profile.id)


@contextmanager
def _unprocessable_when_invalid() -> Iterator[None]:
    """Turns a broken domain invariant, a database constraint or a number
    too large to store into a 422 carrying its message."""
    try:
        yield
    except (ValueError, OverflowError, sqlite3.IntegrityError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _require_known_places(gazetteer: Gazetteer, places: Iterable[PlaceRef]) -> None:
    for place in places:
        if gazetteer.named_place(place) is None:
            raise PlaceNotFoundError(f"{place.kind} {place.code}")


def _profile_model(profile: Profile, gazetteer: Gazetteer) -> ProfileModel:
    named_places: dict[PlaceRef, PlaceMatch] = {}
    for place in (profile.criteria.place, *profile.preferences.preferred_places):
        match = gazetteer.named_place(place)
        if match is not None:
            named_places[place] = match
    return ProfileModel.from_profile(profile, named_places)
