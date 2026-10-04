"""Load config.yaml through the schema. The pipeline consumes the validated
result as a dict whose search place and preferences are typed."""

import difflib
from pathlib import Path

import yaml
from pydantic import ValidationError

from rentczecher_engine.adapters.config.schema import Config, ScoringConfig, StrictModel
from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.adapters.scrapers.location_resolver import resolve
from rentczecher_engine.domain.errors import (
    AmbiguousPlaceError,
    ConfigError,
    ConfigNotFoundError,
    PlaceNotFoundError,
)
from rentczecher_engine.domain.disposition import Disposition, parse_disposition
from rentczecher_engine.domain.location import PlaceKind, PlaceRef
from rentczecher_engine.domain.profile import Preferences

_SEARCHABLE_KINDS: dict[str, PlaceKind] = {"kraj": "kraj", "okres": "okres", "obvod": "obvod"}


def load_config(path: Path) -> dict:
    if not path.exists():
        raise ConfigNotFoundError(f"config not found at {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"{path.name}: expected a mapping at the top level")
    try:
        config = Config.model_validate(raw)
    except ValidationError as error:
        raise ConfigError(_readable(path.name, error)) from error

    loaded = config.model_dump()
    gazetteer = Gazetteer()
    try:
        for profile_id, profile in loaded["profiles"].items():
            search = profile["search"]
            search["place"] = _search_place(gazetteer, search["place"], f"{path.name}: profiles.{profile_id}")
            profile["scoring"] = _preferences(config.profiles[profile_id].scoring)
    finally:
        gazetteer.close()
    return loaded


def _search_place(gazetteer: Gazetteer, text: str, where: str) -> PlaceRef:
    """A search place written as its kind and name, like 'obvod Praha 7'."""
    written_kind, _, name = text.partition(" ")
    kind = _SEARCHABLE_KINDS.get(written_kind.casefold())
    if kind is None:
        raise ConfigError(f"{where}.search.place: name a kraj, okres or obvod, like 'obvod Praha 7'")
    try:
        place = gazetteer.place_named(kind, name)
        resolve(place)
    except (PlaceNotFoundError, AmbiguousPlaceError) as error:
        raise ConfigError(f"{where}.search.place: {error}") from error
    return place


def _preferences(scoring: ScoringConfig) -> Preferences:
    return Preferences(
        price_per_m2_weight=scoring.price_per_m2_weight,
        disposition_weight=scoring.disposition_weight,
        preferred_dispositions=tuple(_disposition(code) for code in scoring.preferred_dispositions),
        size_weight=scoring.size_weight,
        ideal_size_m2=scoring.ideal_size_m2,
        neighborhood_weight=scoring.neighborhood_weight,
        preferred_neighborhoods=tuple(scoring.preferred_neighborhoods),
        land_weight=scoring.land_weight,
        ideal_land_m2=scoring.ideal_land_m2,
        price_weight=scoring.price_weight,
        max_good_price=scoring.max_good_price,
    )


def _disposition(code: str) -> Disposition:
    disposition = parse_disposition(code)
    # The schema has already rejected every code naming no layout.
    assert disposition is not None
    return disposition


def _readable(filename: str, error: ValidationError) -> str:
    lines = []
    for item in error.errors():
        path = ".".join(str(part) for part in item["loc"])
        message = item["msg"]
        if item["type"] == "extra_forbidden":
            message = f"unknown key{_suggestion(item['loc'])}"
        lines.append(f"{filename}: {path}: {message}")
    return "\n".join(lines)


def _suggestion(loc: tuple) -> str:
    bad_key = str(loc[-1])
    candidates = _field_names_at(loc[:-1])
    matches = difflib.get_close_matches(bad_key, candidates, n=1, cutoff=0.6)
    return f" (did you mean '{matches[0]}'?)" if matches else ""


def _field_names_at(parents: tuple) -> list[str]:
    """Key names a user may write at a location path, for typo suggestions."""
    model: type[StrictModel] = Config
    for part in parents:
        fields = getattr(model, "model_fields", {})
        if part in fields:
            annotation = fields[part].annotation
            args = getattr(annotation, "__args__", ())
            # dict[str, Model] fields descend into the value type on the
            # NEXT path part (the dict key), which carries no fields itself.
            model = args[1] if args else annotation
    return list(model.model_fields) if getattr(model, "model_fields", None) else []
