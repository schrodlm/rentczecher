"""Load config.yaml through the schema; the pipeline consumes the validated
result as a plain dict."""

import difflib
from pathlib import Path

import yaml
from pydantic import ValidationError

from rentczecher.adapters.config.schema import Config, StrictModel, field_aliases
from rentczecher.adapters.scrapers.location_resolver import PlaceNotFoundError, resolve
from rentczecher.domain.errors import ConfigError, ConfigNotFoundError


def load_config(path: Path) -> dict:
    if not path.exists():
        raise ConfigNotFoundError(f"config not found at {path}")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ConfigError(f"{path.name}: expected a mapping at the top level")
    try:
        config = Config.model_validate(raw)
    except ValidationError as error:
        raise ConfigError(_readable(path.name, error)) from error

    for profile_id, profile in config.profiles.items():
        try:
            resolve(profile.search.place)
        except PlaceNotFoundError as error:
            raise ConfigError(
                f"{path.name}: profiles.{profile_id}.search.place: {error}"
            ) from error

    dumped = config.model_dump(by_alias=True)
    # SecretStr survives model_dump; the pipeline needs the plain value and
    # this is the one place typed config and plain dicts meet.
    dumped["email"]["smtp_password"] = config.email.smtp_password.get_secret_value()
    return dumped


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
    return field_aliases(model) if getattr(model, "model_fields", None) else []
