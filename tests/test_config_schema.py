"""Tests for the config schema and loader.

Run: python3 -m pytest tests/test_config_schema.py -v
"""

from pathlib import Path

import pytest
import yaml

from rentczecher.adapters.config.loader import load_config
from rentczecher.adapters.config.schema import Config, ProfileConfig
from rentczecher.domain.errors import ConfigError

EXAMPLE = Path(__file__).parent.parent / "config.example.yaml"

VALID = {
    "email": {
        "smtp_host": "smtp.example.com",
        "smtp_user": "u@example.com",
        "smtp_password": "secret",
        "from": "u@example.com",
    },
    "profiles": {
        "p": {
            "name": "P",
            "to": ["a@example.com"],
            "search": {"offer_type": "rent", "estate_type": "flat",
                       "place": "praha-7", "max_price": 25000},
            "scrapers": ["sreality"],
        }
    },
}


def _write(tmp_path, config):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True))
    return path


def _broken(mutate):
    import copy
    config = copy.deepcopy(VALID)
    mutate(config)
    return config


class TestSchemaShape:
    def test_example_config_validates(self):
        """The shipped example must never drift from the schema."""
        Config.model_validate(yaml.safe_load(EXAMPLE.read_text()))

    def test_string_recipient_becomes_list(self):
        profile = ProfileConfig.model_validate({**VALID["profiles"]["p"], "to": "one@example.com"})
        assert profile.to == ["one@example.com"]

    def test_empty_recipient_is_rejected(self):
        with pytest.raises(Exception, match="must not be empty"):
            ProfileConfig.model_validate({**VALID["profiles"]["p"], "to": ""})

    def test_secret_never_appears_in_repr(self):
        config = Config.model_validate(VALID)
        assert "secret" not in repr(config)


class TestPlaceRequired:
    """search.place is the only location source: it is required, must
    resolve, and no portal parameters exist to configure."""

    def test_missing_place_is_rejected(self):
        profile = {
            "name": "P", "to": ["a@example.com"],
            "search": {"offer_type": "rent", "estate_type": "flat"},
            "scrapers": ["sreality"],
        }
        with pytest.raises(Exception, match="place"):
            ProfileConfig.model_validate(profile)

    def test_unknown_place_fails_at_load_with_suggestions(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(place="domzlice"))
        with pytest.raises(ConfigError, match="did you mean.*domazlice"):
            load_config(_write(tmp_path, broken))


class TestScrapersList:
    """A profile's scrapers is a list of known portal names."""

    def test_unknown_scraper_name_gets_a_suggestion(self):
        profile = {**VALID["profiles"]["p"], "scrapers": ["srealty"]}
        with pytest.raises(Exception, match="did you mean 'sreality'"):
            ProfileConfig.model_validate(profile)

    def test_repeated_scraper_name_is_rejected(self):
        profile = {**VALID["profiles"]["p"], "scrapers": ["sreality", "sreality"]}
        with pytest.raises(Exception, match="must not repeat"):
            ProfileConfig.model_validate(profile)

    def test_old_style_parameter_blocks_are_rejected(self):
        # Configs from before place carried per-scraper parameter dicts.
        profile = {**VALID["profiles"]["p"],
                   "scrapers": {"sreality": {"enabled": True, "locality_district_id": 5007}}}
        with pytest.raises(Exception, match="list"):
            ProfileConfig.model_validate(profile)

    def test_known_names_match_the_shipped_scrapers(self):
        from rentczecher.adapters.scrapers import ALL_SCRAPERS
        from rentczecher.adapters.config.schema import KNOWN_SCRAPERS
        assert set(KNOWN_SCRAPERS) == set(ALL_SCRAPERS)


class TestLoader:
    def test_valid_config_loads_as_plain_dict(self, tmp_path):
        config = load_config(_write(tmp_path, VALID))
        assert config["email"]["from"] == "u@example.com"
        assert config["email"]["smtp_password"] == "secret"
        assert config["email"]["smtp_port"] == 587
        assert config["profiles"]["p"]["search"]["min_price"] == 0
        assert config["profiles"]["p"]["scrapers"] == ["sreality"]

    def test_wrong_type_names_the_exact_key(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(max_price="five milion"))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search\.max_price"):
            load_config(_write(tmp_path, broken))

    def test_missing_required_key_is_named(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"].pop("name"))
        with pytest.raises(ConfigError, match=r"profiles\.p\.name"):
            load_config(_write(tmp_path, broken))

    def test_unknown_key_gets_a_suggestion(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(
            dispositons=["2+kk"]))
        with pytest.raises(ConfigError, match=r"dispositons: unknown key \(did you mean 'dispositions'\?\)"):
            load_config(_write(tmp_path, broken))

    def test_unknown_scraper_name_is_an_error(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["scrapers"].append("idnes"))
        with pytest.raises(ConfigError, match="unknown scraper 'idnes'"):
            load_config(_write(tmp_path, broken))



    def test_missing_email_section_fails_at_load(self, tmp_path):
        broken = _broken(lambda c: c.pop("email"))
        with pytest.raises(ConfigError, match="email"):
            load_config(_write(tmp_path, broken))

    def test_invalid_offer_type_is_rejected(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(offer_type="lease"))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search\.offer_type"):
            load_config(_write(tmp_path, broken))



    def test_aliased_field_suggestion_offers_the_yaml_key(self, tmp_path):
        broken = _broken(lambda c: (c["email"].pop("from"), c["email"].update(form="u@example.com")))
        with pytest.raises(ConfigError, match=r"email\.form: unknown key \(did you mean 'from'\?\)"):
            load_config(_write(tmp_path, broken))
