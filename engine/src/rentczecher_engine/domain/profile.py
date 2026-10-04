from dataclasses import dataclass
from typing import Literal

from rentczecher_engine.domain.disposition import Disposition, Kitchen
from rentczecher_engine.domain.location import PlaceRef

OfferType = Literal["rent", "sale"]
EstateType = Literal["flat", "house", "land", "cottage"]


@dataclass(frozen=True, slots=True)
class Criteria:
    """Portal-neutral search intent; scrapers translate it into their
    portal's own parameters."""

    offer_type: OfferType
    estate_type: EstateType
    place: PlaceRef
    min_price: int | None = None
    max_price: int | None = None
    min_size_m2: int | None = None
    min_land_m2: int | None = None
    min_rooms: int | None = None
    max_rooms: int | None = None
    kitchen: Kitchen | None = None

    def __post_init__(self) -> None:
        for name, bound in (("min_price", self.min_price), ("max_price", self.max_price),
                            ("min_size_m2", self.min_size_m2), ("min_land_m2", self.min_land_m2)):
            if bound is not None and bound <= 0:
                raise ValueError(f"{name} must be positive, or left unset for no bound")


@dataclass(frozen=True, slots=True)
class Preferences:
    """A profile's weighted wishes. They raise a listing's score and never
    hide it. A weight of 0 leaves its preference out of the score, and only
    then may the preference's setting be empty."""

    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: tuple[Disposition, ...]
    size_weight: float
    ideal_size_m2: int | None
    place_weight: float
    preferred_places: tuple[PlaceRef, ...]
    land_weight: float
    ideal_land_m2: int | None
    price_weight: float
    max_good_price: int | None

    def __post_init__(self) -> None:
        if self.disposition_weight and not self.preferred_dispositions:
            raise ValueError("disposition_weight needs preferred_dispositions")
        if self.size_weight and (self.ideal_size_m2 is None or self.ideal_size_m2 <= 0):
            raise ValueError("size_weight needs a positive ideal_size_m2")
        if self.place_weight and not self.preferred_places:
            raise ValueError("place_weight needs preferred_places")
        if self.land_weight and (self.ideal_land_m2 is None or self.ideal_land_m2 <= 0):
            raise ValueError("land_weight needs a positive ideal_land_m2")
        if self.price_weight and (self.max_good_price is None or self.max_good_price <= 0):
            raise ValueError("price_weight needs a positive max_good_price")


@dataclass(frozen=True, slots=True)
class Profile:
    """One person's saved search: the portals it scans, the criteria a
    listing must meet to be shown, and the preferences that score it."""

    id: str
    name: str
    enabled: bool
    portals: tuple[str, ...]
    criteria: Criteria
    preferences: Preferences
