"""Load config.yaml through the schema into typed profiles."""

import difflib
from pathlib import Path

import yaml
from pydantic import ValidationError

from rentczecher_engine.adapters.config.schema import (
    Config,
    ProfileConfig,
    ScoringConfig,
    SearchConfig,
    StrictModel,
)
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
from rentczecher_engine.domain.profile import Criteria, Preferences, Profile

_SEARCHABLE_KINDS: dict[str, PlaceKind] = {"kraj": "kraj", "okres": "okres", "obvod": "obvod"}
_PLACE_KINDS: dict[str, PlaceKind] = {
    "kraj": "kraj",
    "okres": "okres",
    "obec": "obec",
    "obvod": "obvod",
    "mestska_cast": "mestska_cast",
    "cast_obce": "cast_obce",
    "ulice": "ulice",
}


def load_config(path: Path) -> list[Profile]:
    if not path.exists():
        raise ConfigNotFoundError(f"config not found at {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"{path.name}: expected a mapping at the top level")
    try:
        config = Config.model_validate(raw)
    except ValidationError as error:
        raise ConfigError(_readable(path.name, error)) from error

    gazetteer = Gazetteer()
    try:
        return [_profile(gazetteer, profile_id, written, f"{path.name}: profiles.{profile_id}")
                for profile_id, written in config.profiles.items()]
    finally:
        gazetteer.close()


def _profile(gazetteer: Gazetteer, profile_id: str, written: ProfileConfig, where: str) -> Profile:
    place = _search_place(gazetteer, written.search.place, where)
    return Profile(
        id=profile_id,
        name=written.name,
        enabled=written.enabled,
        portals=tuple(written.scrapers),
        criteria=_criteria(written.search, place, where),
        preferences=_preferences(gazetteer, written.scoring, where),
    )


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


def _preferred_place(gazetteer: Gazetteer, text: str, where: str) -> PlaceRef:
    """A preferred place written as its kind and name, like 'cast_obce Bubeneč'."""
    written_kind, _, name = text.partition(" ")
    kind = _PLACE_KINDS.get(written_kind.casefold())
    if kind is None:
        raise ConfigError(f"{where}.scoring.preferred_places: start {text!r} with its kind, "
                          f"one of {', '.join(_PLACE_KINDS)}")
    try:
        return gazetteer.place_named(kind, name)
    except (PlaceNotFoundError, AmbiguousPlaceError) as error:
        raise ConfigError(f"{where}.scoring.preferred_places: {error}") from error


def _criteria(search: SearchConfig, place: PlaceRef, where: str) -> Criteria:
    try:
        return Criteria(
            offer_type=search.offer_type,
            estate_type=search.estate_type,
            place=place,
            min_price=search.min_price,
            max_price=search.max_price,
            min_size_m2=search.min_size_m2,
            min_land_m2=search.min_land_m2,
            min_rooms=search.min_rooms,
            max_rooms=search.max_rooms,
            kitchen=search.kitchen,
        )
    except ValueError as error:
        raise ConfigError(f"{where}.search: {error}") from error


def _preferences(gazetteer: Gazetteer, scoring: ScoringConfig, where: str) -> Preferences:
    preferred_places = tuple(_preferred_place(gazetteer, text, where) for text in scoring.preferred_places)
    try:
        return Preferences(
            price_per_m2_weight=scoring.price_per_m2_weight,
            disposition_weight=scoring.disposition_weight,
            preferred_dispositions=tuple(_disposition(code) for code in scoring.preferred_dispositions),
            size_weight=scoring.size_weight,
            ideal_size_m2=scoring.ideal_size_m2,
            place_weight=scoring.place_weight,
            preferred_places=preferred_places,
            land_weight=scoring.land_weight,
            ideal_land_m2=scoring.ideal_land_m2,
            price_weight=scoring.price_weight,
            max_good_price=scoring.max_good_price,
        )
    except ValueError as error:
        raise ConfigError(f"{where}.scoring: {error}") from error


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
