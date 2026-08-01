"""Typed schema for config.yaml: the single home for shape, defaults, and
normalization. Everything downstream consumes the validated result."""

import difflib

from pydantic import (
    BaseModel, ConfigDict, Field, SecretStr, ValidationError,
    field_validator, model_validator,
)
from typing import Literal


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


class SrealityScraperConfig(StrictModel):
    enabled: bool = False
    category_main_cb: int = 1
    category_type_cb: int = 2
    locality_district_id: int | None = None
    category_sub_cb: str | None = None

    @model_validator(mode="after")
    def _district_required_when_enabled(self):
        if self.enabled and self.locality_district_id is None:
            raise ValueError("locality_district_id is required when sreality is enabled")
        return self


class BezrealitkyScraperConfig(StrictModel):
    enabled: bool = False
    estate_type: str = "BYT"
    offer_type: str = "PRONAJEM"
    region_osm_id: str | None = None
    osm_value: str | None = None


class RemaxScraperConfig(StrictModel):
    enabled: bool = False
    search_url: str | None = None


ScraperConfig = SrealityScraperConfig | BezrealitkyScraperConfig | RemaxScraperConfig

SCRAPER_MODELS: dict[str, type[StrictModel]] = {
    "sreality": SrealityScraperConfig,
    "bezrealitky": BezrealitkyScraperConfig,
    "remax": RemaxScraperConfig,
}


class ProfileConfig(StrictModel):
    name: str
    enabled: bool = True
    to: list[str]
    search: SearchConfig
    scrapers: dict[str, ScraperConfig]
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

    @field_validator("scrapers", mode="before")
    @classmethod
    def _dispatch_scraper_models(cls, value):
        # Dispatching by dict key hides the scraper name from pydantic's
        # error paths, so nested errors are reformatted to carry it.
        if not isinstance(value, dict):
            return value
        dispatched = {}
        for key, cfg in value.items():
            model = SCRAPER_MODELS.get(key)
            if model is None:
                raise ValueError(f"unknown scraper '{key}' (known: {sorted(SCRAPER_MODELS)})")
            try:
                dispatched[key] = model.model_validate(cfg)
            except ValidationError as error:
                raise ValueError(_scraper_errors(key, model, error)) from error
        return dispatched


class Config(StrictModel):
    email: EmailConfig
    profiles: dict[str, ProfileConfig]
    schedule: ScheduleConfig = ScheduleConfig()


def field_aliases(model: type[BaseModel]) -> list[str]:
    """The key names a user may actually write for a model (aliases win)."""
    return [field.alias or name for name, field in model.model_fields.items()]


def _scraper_errors(key: str, model: type[BaseModel], error: ValidationError) -> str:
    lines = []
    for item in error.errors():
        path = ".".join(str(part) for part in item["loc"])
        message = item["msg"]
        if item["type"] == "extra_forbidden":
            matches = difflib.get_close_matches(str(item["loc"][-1]), field_aliases(model), n=1, cutoff=0.6)
            message = f"unknown key (did you mean '{matches[0]}'?)" if matches else "unknown key"
        lines.append(f"{key}.{path}: {message}" if path else f"{key}: {message}")
    return "; ".join(lines)
