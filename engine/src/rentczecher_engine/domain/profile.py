import math
from dataclasses import dataclass
from typing import Literal

from rentczecher_engine.domain.disposition import Disposition, Kitchen
from rentczecher_engine.domain.location import PlaceRef

OfferType = Literal["rent", "sale"]
EstateType = Literal["flat", "house", "land", "cottage"]
Portal = Literal["sreality", "bezrealitky", "remax"]


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
    max_size_m2: int | None = None
    min_land_m2: int | None = None
    min_rooms: int | None = None
    max_rooms: int | None = None
    kitchen: Kitchen | None = None

    def __post_init__(self) -> None:
        if self.min_price is not None and self.min_price <= 0:
            raise ValueError("min_price must be positive, or left unset for no bound")
        if self.max_price is not None and self.max_price <= 0:
            raise ValueError("max_price must be positive, or left unset for no bound")
        if self.min_size_m2 is not None and self.min_size_m2 <= 0:
            raise ValueError("min_size_m2 must be positive, or left unset for no bound")
        if self.max_size_m2 is not None and self.max_size_m2 <= 0:
            raise ValueError("max_size_m2 must be positive, or left unset for no bound")
        if self.min_land_m2 is not None and self.min_land_m2 <= 0:
            raise ValueError("min_land_m2 must be positive, or left unset for no bound")
        if self.min_rooms is not None and not 1 <= self.min_rooms <= 9:
            raise ValueError("min_rooms must be 1 to 9, or left unset for no bound")
        if self.max_rooms is not None and not 1 <= self.max_rooms <= 9:
            raise ValueError("max_rooms must be 1 to 9, or left unset for no bound")
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must not exceed max_price")
        if self.min_size_m2 is not None and self.max_size_m2 is not None and self.min_size_m2 > self.max_size_m2:
            raise ValueError("min_size_m2 must not exceed max_size_m2")
        if self.min_rooms is not None and self.max_rooms is not None and self.min_rooms > self.max_rooms:
            raise ValueError("min_rooms must not exceed max_rooms")


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
        weights = {
            "price_per_m2_weight": self.price_per_m2_weight,
            "disposition_weight": self.disposition_weight,
            "size_weight": self.size_weight,
            "place_weight": self.place_weight,
            "land_weight": self.land_weight,
            "price_weight": self.price_weight,
        }
        for name, weight in weights.items():
            if not math.isfinite(weight) or weight < 0:
                raise ValueError(f"{name} must be finite and not negative")
        if len(set(self.preferred_dispositions)) != len(self.preferred_dispositions):
            raise ValueError("preferred_dispositions must not repeat")
        if len(set(self.preferred_places)) != len(self.preferred_places):
            raise ValueError("preferred_places must not repeat")
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
    paused_at: str | None
    portals: tuple[Portal, ...]
    criteria: Criteria
    preferences: Preferences

    def __post_init__(self) -> None:
        if len(set(self.portals)) != len(self.portals):
            raise ValueError("portals must not repeat")
