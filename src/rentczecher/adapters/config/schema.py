"""Typed schema for config.yaml: the single home for shape, defaults, and
normalization. Everything downstream consumes the validated result."""

import difflib

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from typing import Literal

KNOWN_SCRAPERS = ("sreality", "bezrealitky", "remax")


class StrictModel(BaseModel):
    # Unknown keys are errors: a typo must fail at load time, never no-op.
    model_config = ConfigDict(extra="forbid")


class EmailConfig(StrictModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: SecretStr
    from_: str = Field(alias="from")


class ScheduleConfig(StrictModel):
    cron_interval_hours: int = 3


class SearchConfig(StrictModel):
    offer_type: Literal["rent", "sale"]
    estate_type: Literal["flat", "house", "land", "cottage"]
    place: str
    min_price: int = 0
    max_price: int = 25000
    dispositions: list[str] = []
    min_size_m2: int = 0
    min_land_m2: int = 0


class ScoringConfig(StrictModel):
    price_per_m2_weight: float = 0
    disposition_weight: float = 0
    preferred_dispositions: list[str] = []
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
    to: list[str]
    search: SearchConfig
    scrapers: list[str]
    scoring: ScoringConfig = ScoringConfig()
    tram_enrichment: bool = False

    @field_validator("to", mode="before")
    @classmethod
    def _string_becomes_list(cls, value):
        return [value] if isinstance(value, str) else value

    @field_validator("to")
    @classmethod
    def _no_empty_recipients(cls, value):
        if any(not recipient.strip() for recipient in value):
            raise ValueError("recipient addresses must not be empty")
        return value

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
    email: EmailConfig
    profiles: dict[str, ProfileConfig]
    schedule: ScheduleConfig = ScheduleConfig()


def field_aliases(model: type[BaseModel]) -> list[str]:
    """The key names a user may actually write for a model (aliases win)."""
    return [field.alias or name for name, field in model.model_fields.items()]
