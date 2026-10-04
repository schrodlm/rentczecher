from dataclasses import dataclass

from rentczecher_engine.domain.disposition import Disposition


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
