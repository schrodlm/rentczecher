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

from rentczecher_engine.adapters.api.photo_links import PhotoLinks
from rentczecher_engine.adapters.api.run_manager import PortalHealthEntry
from rentczecher_engine.domain.disposition import Disposition, DispositionCode, parse_disposition
from rentczecher_engine.domain.geo import GeoPoint
from rentczecher_engine.domain.photo import Gallery, GalleryStatus
from rentczecher_engine.domain.property import TrackedProperty
from rentczecher_engine.domain.location import Location, Place, PlaceKind, PlaceMatch, PlaceRef
from rentczecher_engine.domain.price import PostingPrices, PriceChange
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
    max_size_m2: int | None
    min_land_m2: int | None
    dispositions: list[DispositionCode]

    def to_criteria(self) -> Criteria:
        return Criteria(
            offer_type=self.offer_type,
            estate_type=self.estate_type,
            place=self.place.to_place_ref(),
            min_price=self.min_price,
            max_price=self.max_price,
            min_size_m2=self.min_size_m2,
            max_size_m2=self.max_size_m2,
            min_land_m2=self.min_land_m2,
            dispositions=tuple(_disposition(code) for code in self.dispositions),
        )


class PreferencesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: list[DispositionCode]
    size_weight: float
    preferred_size_m2: int | None
    place_weight: float
    preferred_places: list[PlaceRefModel]
    land_weight: float
    preferred_land_m2: int | None
    price_weight: float
    preferred_price: int | None

    def to_preferences(self) -> Preferences:
        return Preferences(
            price_per_m2_weight=self.price_per_m2_weight,
            disposition_weight=self.disposition_weight,
            preferred_dispositions=tuple(_disposition(code) for code in self.preferred_dispositions),
            size_weight=self.size_weight,
            preferred_size_m2=self.preferred_size_m2,
            place_weight=self.place_weight,
            preferred_places=tuple(place.to_place_ref() for place in self.preferred_places),
            land_weight=self.land_weight,
            preferred_land_m2=self.preferred_land_m2,
            price_weight=self.price_weight,
            preferred_price=self.preferred_price,
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
    max_size_m2: int | None
    min_land_m2: int | None
    dispositions: list[DispositionCode]

    @classmethod
    def from_criteria(cls, criteria: Criteria, named_places: Mapping[PlaceRef, PlaceMatch]) -> "CriteriaModel":
        return cls(
            offer_type=criteria.offer_type,
            estate_type=criteria.estate_type,
            place=NamedPlaceModel.from_place(criteria.place, named_places),
            min_price=criteria.min_price,
            max_price=criteria.max_price,
            min_size_m2=criteria.min_size_m2,
            max_size_m2=criteria.max_size_m2,
            min_land_m2=criteria.min_land_m2,
            dispositions=[disposition.code for disposition in criteria.dispositions],
        )


class PreferencesModel(BaseModel):
    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: list[DispositionCode]
    size_weight: float
    preferred_size_m2: int | None
    place_weight: float
    preferred_places: list[NamedPlaceModel]
    land_weight: float
    preferred_land_m2: int | None
    price_weight: float
    preferred_price: int | None

    @classmethod
    def from_preferences(cls, preferences: Preferences,
                         named_places: Mapping[PlaceRef, PlaceMatch]) -> "PreferencesModel":
        return cls(
            price_per_m2_weight=preferences.price_per_m2_weight,
            disposition_weight=preferences.disposition_weight,
            preferred_dispositions=[disposition.code for disposition in preferences.preferred_dispositions],
            size_weight=preferences.size_weight,
            preferred_size_m2=preferences.preferred_size_m2,
            place_weight=preferences.place_weight,
            preferred_places=[NamedPlaceModel.from_place(place, named_places)
                              for place in preferences.preferred_places],
            land_weight=preferences.land_weight,
            preferred_land_m2=preferences.preferred_land_m2,
            price_weight=preferences.price_weight,
            preferred_price=preferences.preferred_price,
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


class PointModel(BaseModel):
    lat: float
    lon: float

    @classmethod
    def from_point(cls, point: GeoPoint) -> "PointModel":
        return cls(lat=point.lat, lon=point.lon)


class PhotoModel(BaseModel):
    url: str = Field(description="A signed link valid while the engine runs, relative to its address.")


class TrackedPropertyModel(BaseModel):
    id: str
    listing_id: str
    source: str
    url: str
    title: str | None
    location_raw_text: str | None
    resolved_location: LocationModel | None
    point: PointModel | None
    size_m2: int | None
    land_m2: int | None
    disposition_raw_text: str | None
    disposition: str | None
    first_seen_at: str
    viewed_at: str | None
    favourited_at: str | None
    price: int | None
    price_drop_from: int | None
    sibling_sources: list[SiblingSourceModel]
    main_photo: PhotoModel | None

    @classmethod
    def from_tracked_property(cls, tracked: TrackedProperty, resolved_location: Location | None,
                              main_photo: PhotoModel | None) -> "TrackedPropertyModel":
        return cls(
            id=tracked.id,
            listing_id=tracked.listing_id,
            source=tracked.source,
            url=tracked.url,
            title=tracked.title,
            location_raw_text=tracked.location_raw_text,
            resolved_location=LocationModel.from_location(resolved_location) if resolved_location else None,
            point=PointModel.from_point(tracked.point) if tracked.point is not None else None,
            size_m2=tracked.size_m2,
            land_m2=tracked.land_m2,
            disposition_raw_text=tracked.disposition_raw_text,
            disposition=tracked.disposition.code if tracked.disposition is not None else None,
            first_seen_at=tracked.first_seen_at,
            viewed_at=tracked.viewed_at,
            favourited_at=tracked.favourited_at,
            price=tracked.price,
            price_drop_from=tracked.price_drop_from,
            sibling_sources=[
                SiblingSourceModel(source=sibling.source, url=sibling.url)
                for sibling in tracked.sibling_sources
            ],
            main_photo=main_photo,
        )


class PriceChangeModel(BaseModel):
    price: int
    charges: int | None
    first_seen_at: str
    last_seen_at: str

    @classmethod
    def from_change(cls, change: PriceChange) -> "PriceChangeModel":
        return cls(
            price=change.price,
            charges=change.charges,
            first_seen_at=change.first_seen_at,
            last_seen_at=change.last_seen_at,
        )


class PostingPricesModel(BaseModel):
    listing_id: str
    source: str
    url: str
    changes: list[PriceChangeModel]

    @classmethod
    def from_posting(cls, posting: PostingPrices) -> "PostingPricesModel":
        return cls(
            listing_id=posting.listing_id,
            source=posting.source,
            url=posting.url,
            changes=[PriceChangeModel.from_change(change) for change in posting.changes],
        )


class GalleryModel(BaseModel):
    """A tracked property's photos: those of its listing with the most
    photos, which may be another portal's than the one it is shown by."""

    status: GalleryStatus
    source: str
    posting_url: str
    photo_count: int = Field(description="How many photos are known, stored or not, the count growing once "
                                         "the advert's own page is read.")
    photos: list[PhotoModel] = Field(description="The stored photos, in the portal's order.")

    @classmethod
    def from_gallery(cls, gallery: Gallery, links: PhotoLinks) -> "GalleryModel":
        return cls(
            status=gallery.status,
            source=gallery.source,
            posting_url=gallery.url,
            photo_count=gallery.photo_count,
            photos=[PhotoModel(url=links.link(file_key)) for file_key in gallery.file_keys],
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
