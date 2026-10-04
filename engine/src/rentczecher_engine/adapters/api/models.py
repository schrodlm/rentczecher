"""Pydantic response models for the sidecar API: the single source of truth
for the wire contract.

The chain runs one way. These classes generate the OpenAPI schema (a
language-neutral JSON description of every endpoint and shape), and the
GUI's TypeScript types are generated from that schema. Python is never
generated from anything, it is the origin. A field renamed here is
therefore a contract change the GUI is rebuilt against, not an internal
refactor."""

from typing import Literal

from pydantic import BaseModel

from rentczecher_engine.adapters.api.run_manager import PortalHealthEntry
from rentczecher_engine.domain.listing import InboxCard
from rentczecher_engine.domain.location import Location, Place
from rentczecher_engine.domain.profile import Profile


class ProfileModel(BaseModel):
    id: str
    name: str
    enabled: bool

    @classmethod
    def from_profile(cls, profile: Profile) -> "ProfileModel":
        return cls(id=profile.id, name=profile.name, enabled=profile.paused_at is None)


class SiblingSourceModel(BaseModel):
    source: str
    url: str


class PlaceModel(BaseModel):
    code: int
    name: str

    @classmethod
    def from_place(cls, place: Place) -> "PlaceModel":
        return cls(code=place.code, name=place.name)


class LocationModel(BaseModel):
    kraj: PlaceModel
    okres: PlaceModel | None
    obec: PlaceModel | None
    obvod: PlaceModel | None
    mestska_cast: PlaceModel | None
    cast_obce: PlaceModel | None
    ulice: PlaceModel | None
    cislo_popisne: str | None
    cislo_orientacni: str | None

    @classmethod
    def from_location(cls, location: Location) -> "LocationModel":
        return cls(
            kraj=PlaceModel.from_place(location.kraj),
            okres=PlaceModel.from_place(location.okres) if location.okres else None,
            obec=PlaceModel.from_place(location.obec) if location.obec else None,
            obvod=PlaceModel.from_place(location.obvod) if location.obvod else None,
            mestska_cast=PlaceModel.from_place(location.mestska_cast) if location.mestska_cast else None,
            cast_obce=PlaceModel.from_place(location.cast_obce) if location.cast_obce else None,
            ulice=PlaceModel.from_place(location.ulice) if location.ulice else None,
            cislo_popisne=location.cislo_popisne,
            cislo_orientacni=location.cislo_orientacni,
        )


class ListingModel(BaseModel):
    id: str
    source: str
    url: str
    title: str | None
    location_raw_text: str | None
    resolved_location: LocationModel | None
    size_m2: int | None
    disposition_raw_text: str | None
    disposition: str | None
    first_seen_at: str
    viewed_at: str | None
    favourited_at: str | None
    price: int | None
    price_drop_from: int | None
    sibling_sources: list[SiblingSourceModel]

    @classmethod
    def from_card(cls, card: InboxCard, resolved_location: Location | None) -> "ListingModel":
        return cls(
            id=card.id,
            source=card.source,
            url=card.url,
            title=card.title,
            location_raw_text=card.location_raw_text,
            resolved_location=LocationModel.from_location(resolved_location) if resolved_location else None,
            size_m2=card.size_m2,
            disposition_raw_text=card.disposition_raw_text,
            disposition=card.disposition.code if card.disposition is not None else None,
            first_seen_at=card.first_seen_at,
            viewed_at=card.viewed_at,
            favourited_at=card.favourited_at,
            price=card.price,
            price_drop_from=card.price_drop_from,
            sibling_sources=[
                SiblingSourceModel(source=sibling.source, url=sibling.url)
                for sibling in card.sibling_sources
            ],
        )


class RunTriggeredModel(BaseModel):
    run_id: str
    profile_id: str


class PortalHealthModel(BaseModel):
    portal: str
    status: Literal["ok", "broken", "zero_results"]
    error: str | None
    listing_count: int
    checked_at: str

    @classmethod
    def from_entry(cls, portal: str, entry: PortalHealthEntry) -> "PortalHealthModel":
        return cls(
            portal=portal, status=entry.status, error=entry.error,
            listing_count=entry.listing_count, checked_at=entry.checked_at,
        )
