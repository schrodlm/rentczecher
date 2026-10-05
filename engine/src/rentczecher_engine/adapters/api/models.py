"""Pydantic request and response models for the sidecar API: the single
source of truth for the wire contract.

The chain runs one way. These classes generate the OpenAPI schema (a
language-neutral JSON description of every endpoint and shape), and the
GUI's TypeScript types are generated from that schema. Python is never
generated from anything, it is the origin. A field renamed here is
therefore a contract change the GUI is rebuilt against, not an internal
refactor."""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from rentczecher_engine.adapters.api.run_manager import PortalHealthEntry
from rentczecher_engine.domain.disposition import Disposition, DispositionCode, Kitchen, parse_disposition
from rentczecher_engine.domain.listing import InboxCard
from rentczecher_engine.domain.location import Location, Place, PlaceKind, PlaceMatch, PlaceRef
from rentczecher_engine.domain.profile import Criteria, EstateType, OfferType, Portal, Preferences, Profile


class PlaceRefModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PlaceKind
    # RÚIAN codes are positive, and the gazetteer stores them as 64-bit integers.
    code: int = Field(gt=0, lt=2**63)

    def to_place_ref(self) -> PlaceRef:
        return PlaceRef(kind=self.kind, code=self.code)


class NamedPlaceModel(BaseModel):
    """A place with its name and the names of the obec and okres it lies
    in. The name is None only for a stored place the gazetteer no longer
    knows."""

    kind: PlaceKind
    code: int
    name: str | None
    obec: str | None
    okres: str | None

    @classmethod
    def from_match(cls, match: PlaceMatch) -> "NamedPlaceModel":
        return cls(kind=match.place.kind, code=match.place.code, name=match.name,
                   obec=match.obec, okres=match.okres)

    @classmethod
    def from_place(cls, place: PlaceRef, named_places: Mapping[PlaceRef, PlaceMatch]) -> "NamedPlaceModel":
        match = named_places.get(place)
        if match is None:
            return cls(kind=place.kind, code=place.code, name=None, obec=None, okres=None)
        return cls.from_match(match)


class CriteriaBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_type: OfferType
    estate_type: EstateType
    place: PlaceRefModel
    min_price: int | None
    max_price: int | None
    min_size_m2: int | None
    min_land_m2: int | None
    min_rooms: int | None
    max_rooms: int | None
    kitchen: Kitchen | None

    def to_criteria(self) -> Criteria:
        return Criteria(
            offer_type=self.offer_type,
            estate_type=self.estate_type,
            place=self.place.to_place_ref(),
            min_price=self.min_price,
            max_price=self.max_price,
            min_size_m2=self.min_size_m2,
            min_land_m2=self.min_land_m2,
            min_rooms=self.min_rooms,
            max_rooms=self.max_rooms,
            kitchen=self.kitchen,
        )


class PreferencesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: list[DispositionCode]
    size_weight: float
    ideal_size_m2: int | None
    place_weight: float
    preferred_places: list[PlaceRefModel]
    land_weight: float
    ideal_land_m2: int | None
    price_weight: float
    max_good_price: int | None

    def to_preferences(self) -> Preferences:
        return Preferences(
            price_per_m2_weight=self.price_per_m2_weight,
            disposition_weight=self.disposition_weight,
            preferred_dispositions=tuple(_disposition(code) for code in self.preferred_dispositions),
            size_weight=self.size_weight,
            ideal_size_m2=self.ideal_size_m2,
            place_weight=self.place_weight,
            preferred_places=tuple(place.to_place_ref() for place in self.preferred_places),
            land_weight=self.land_weight,
            ideal_land_m2=self.ideal_land_m2,
            price_weight=self.price_weight,
            max_good_price=self.max_good_price,
        )


class NewProfileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    portals: list[Portal]
    criteria: CriteriaBody
    preferences: PreferencesBody


class ProfileUpdateBody(BaseModel):
    """Everything about a profile but its criteria, which stay as created."""

    model_config = ConfigDict(extra="forbid")

    name: str
    paused: bool
    portals: list[Portal]
    preferences: PreferencesBody


class CriteriaModel(BaseModel):
    offer_type: OfferType
    estate_type: EstateType
    place: NamedPlaceModel
    min_price: int | None
    max_price: int | None
    min_size_m2: int | None
    min_land_m2: int | None
    min_rooms: int | None
    max_rooms: int | None
    kitchen: Kitchen | None

    @classmethod
    def from_criteria(cls, criteria: Criteria, named_places: Mapping[PlaceRef, PlaceMatch]) -> "CriteriaModel":
        return cls(
            offer_type=criteria.offer_type,
            estate_type=criteria.estate_type,
            place=NamedPlaceModel.from_place(criteria.place, named_places),
            min_price=criteria.min_price,
            max_price=criteria.max_price,
            min_size_m2=criteria.min_size_m2,
            min_land_m2=criteria.min_land_m2,
            min_rooms=criteria.min_rooms,
            max_rooms=criteria.max_rooms,
            kitchen=criteria.kitchen,
        )


class PreferencesModel(BaseModel):
    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: list[DispositionCode]
    size_weight: float
    ideal_size_m2: int | None
    place_weight: float
    preferred_places: list[NamedPlaceModel]
    land_weight: float
    ideal_land_m2: int | None
    price_weight: float
    max_good_price: int | None

    @classmethod
    def from_preferences(cls, preferences: Preferences,
                         named_places: Mapping[PlaceRef, PlaceMatch]) -> "PreferencesModel":
        return cls(
            price_per_m2_weight=preferences.price_per_m2_weight,
            disposition_weight=preferences.disposition_weight,
            preferred_dispositions=[disposition.code for disposition in preferences.preferred_dispositions],
            size_weight=preferences.size_weight,
            ideal_size_m2=preferences.ideal_size_m2,
            place_weight=preferences.place_weight,
            preferred_places=[NamedPlaceModel.from_place(place, named_places)
                              for place in preferences.preferred_places],
            land_weight=preferences.land_weight,
            ideal_land_m2=preferences.ideal_land_m2,
            price_weight=preferences.price_weight,
            max_good_price=preferences.max_good_price,
        )


class ProfileModel(BaseModel):
    id: str
    name: str
    paused_at: str | None
    portals: list[Portal]
    criteria: CriteriaModel
    preferences: PreferencesModel

    @classmethod
    def from_profile(cls, profile: Profile, named_places: Mapping[PlaceRef, PlaceMatch]) -> "ProfileModel":
        return cls(
            id=profile.id,
            name=profile.name,
            paused_at=profile.paused_at,
            portals=list(profile.portals),
            criteria=CriteriaModel.from_criteria(profile.criteria, named_places),
            preferences=PreferencesModel.from_preferences(profile.preferences, named_places),
        )


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


def _disposition(code: DispositionCode) -> Disposition:
    disposition = parse_disposition(code)
    # Every DispositionCode is a canonical code the parser reads back.
    assert disposition is not None
    return disposition
