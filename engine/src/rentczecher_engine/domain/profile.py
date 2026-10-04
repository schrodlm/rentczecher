from dataclasses import dataclass

from rentczecher_engine.domain.disposition import Disposition, Kitchen
from rentczecher_engine.domain.location import PlaceRef


@dataclass(frozen=True, slots=True)
class Criteria:
    """Portal-neutral search intent; scrapers translate it into their
    portal's own parameters."""

    offer_type: str
    estate_type: str
    place: PlaceRef
    min_price: int = 0
    max_price: int = 0
    min_size_m2: int = 0
    min_land_m2: int = 0
    min_rooms: int | None = None
    max_rooms: int | None = None
    kitchen: Kitchen | None = None


@dataclass(frozen=True, slots=True)
class Preferences:
    """A profile's weighted wishes. They raise a listing's score and never
    hide it. A weight of 0 leaves its preference out of the score."""

    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: tuple[Disposition, ...]
    size_weight: float
    ideal_size_m2: int
    place_weight: float
    preferred_places: tuple[PlaceRef, ...]
    land_weight: float
    ideal_land_m2: int
    price_weight: float
    max_good_price: int


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
