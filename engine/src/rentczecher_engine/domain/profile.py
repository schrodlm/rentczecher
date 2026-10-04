from dataclasses import dataclass

from rentczecher_engine.domain.disposition import Disposition
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
    dispositions: tuple[str, ...] = ()

    @classmethod
    def from_search_config(cls, search: dict) -> "Criteria":
        return cls(
            offer_type=search["offer_type"],
            estate_type=search["estate_type"],
            place=search["place"],
            min_price=search.get("min_price", 0),
            max_price=search.get("max_price", 0),
            min_size_m2=search.get("min_size_m2", 0),
            min_land_m2=search.get("min_land_m2", 0),
            dispositions=tuple(search.get("dispositions", ())),
        )


@dataclass(frozen=True, slots=True)
class Preferences:
    """A profile's weighted wishes. They raise a listing's score and never
    hide it. A weight of 0 leaves its preference out of the score."""

    price_per_m2_weight: float
    disposition_weight: float
    preferred_dispositions: tuple[Disposition, ...]
    size_weight: float
    ideal_size_m2: int
    neighborhood_weight: float
    preferred_neighborhoods: tuple[str, ...]
    land_weight: float
    ideal_land_m2: int
    price_weight: float
    max_good_price: int
