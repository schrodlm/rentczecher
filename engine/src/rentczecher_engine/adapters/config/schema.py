"""Typed schema for config.yaml: the single home for shape, defaults, and
normalization. Everything downstream consumes the validated result."""

import difflib

from pydantic import AfterValidator, BaseModel, ConfigDict, field_validator
from typing import Annotated, Literal

from rentczecher_engine.domain.disposition import parse_disposition

KNOWN_SCRAPERS = ("sreality", "bezrealitky", "remax")


class StrictModel(BaseModel):
    # Unknown keys are errors: a typo must fail at load time, never no-op.
    model_config = ConfigDict(extra="forbid")


def _layouts_only(values: list[str]) -> list[str]:
    unknown = [value for value in values if parse_disposition(value) is None]
    if unknown:
        raise ValueError(f"not a disposition: {', '.join(unknown)} (use forms like 2+kk, 3+1 or atypicky)")
    return values


DispositionCodes = Annotated[list[str], AfterValidator(_layouts_only)]


class ScheduleConfig(StrictModel):
    cron_interval_hours: int = 3


class SearchConfig(StrictModel):
    offer_type: Literal["rent", "sale"]
    estate_type: Literal["flat", "house", "land", "cottage"]
    place: str
    min_price: int = 0
    max_price: int = 25000
    dispositions: DispositionCodes = []
    min_size_m2: int = 0
    min_land_m2: int = 0


class ScoringConfig(StrictModel):
    price_per_m2_weight: float = 0
    disposition_weight: float = 0
    preferred_dispositions: DispositionCodes = []
    size_weight: float = 0
    ideal_size_m2: int = 55
    neighborhood_weight: float = 0
    preferred_neighborhoods: list[str] = []
    land_weight: float = 0
    ideal_land_m2: int = 2000
    price_weight: float = 0
    max_good_price: int = 3000000


class ProfileConfig(StrictModel):
    name: str
    enabled: bool = True
    search: SearchConfig
    scrapers: list[str]
    scoring: ScoringConfig = ScoringConfig()

    @field_validator("scrapers")
    @classmethod
    def _known_scraper_names(cls, value):
        for name in value:
            if name not in KNOWN_SCRAPERS:
                matches = difflib.get_close_matches(name, KNOWN_SCRAPERS, n=1, cutoff=0.6)
                hint = f" (did you mean '{matches[0]}'?)" if matches else ""
                raise ValueError(f"unknown scraper '{name}'{hint} (known: {sorted(KNOWN_SCRAPERS)})")
        if len(set(value)) != len(value):
            raise ValueError("scraper names must not repeat")
        return value


class Config(StrictModel):
    profiles: dict[str, ProfileConfig]
    schedule: ScheduleConfig = ScheduleConfig()
