"""Tests for the config schema and loader.

Run: python3 -m pytest tests/test_config_schema.py -v
"""

import copy
from pathlib import Path

import pytest
import yaml

from rentczecher_engine.adapters.config.loader import load_config
from rentczecher_engine.adapters.config.schema import Config, ProfileConfig
from rentczecher_engine.domain.errors import ConfigError, ConfigNotFoundError

EXAMPLE = Path(__file__).parent.parent / "config.example.yaml"

VALID = {
    "profiles": {
        "p": {
            "name": "P",
            "search": {"offer_type": "rent", "estate_type": "flat",
                       "place": "obvod Praha 7", "max_price": 25000},
            "scrapers": ["sreality"],
        }
    },
}


def _write(tmp_path, config):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True))
    return path


def _broken(mutate):
    config = copy.deepcopy(VALID)
    mutate(config)
    return config


class TestSchemaShape:
    def test_example_config_validates(self):
        """The shipped example must never drift from the schema."""
        Config.model_validate(yaml.safe_load(EXAMPLE.read_text()))


class TestPlaceRequired:
    """search.place is the only location source: it is required, must
    resolve, and no portal parameters exist to configure."""

    def test_missing_place_is_rejected(self):
        profile = {
            "name": "P",
            "search": {"offer_type": "rent", "estate_type": "flat"},
            "scrapers": ["sreality"],
        }
        with pytest.raises(Exception, match="place"):
            ProfileConfig.model_validate(profile)

    def test_unknown_place_fails_at_load(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(place="okres Domzlice"))
        with pytest.raises(ConfigError, match="unknown place"):
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
        from rentczecher_engine.adapters.scrapers import ALL_SCRAPERS
        from rentczecher_engine.adapters.config.schema import KNOWN_SCRAPERS
        assert set(KNOWN_SCRAPERS) == set(ALL_SCRAPERS)


class TestLoader:
    def test_missing_file_raises_config_not_found_naming_the_path(self, tmp_path):
        """A nonexistent config file is a ConfigError like any other, so
        every caller reports it through one channel."""
        missing = tmp_path / "config.yaml"
        with pytest.raises(ConfigNotFoundError, match="config not found at"):
            load_config(missing)

    def test_valid_config_loads_as_plain_dict(self, tmp_path):
        config = load_config(_write(tmp_path, VALID))
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

    def test_unparseable_criterion_disposition_is_named(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(dispositions=["2+kk", "2+2"]))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search\.dispositions.*not a disposition: 2\+2"):
            load_config(_write(tmp_path, broken))

    def test_unparseable_preferred_disposition_is_named(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"].update(
            scoring={"disposition_weight": 30, "preferred_dispositions": ["Rodinný"]}))
        with pytest.raises(ConfigError,
                           match=r"profiles\.p\.scoring\.preferred_dispositions.*not a disposition: Rodinný"):
            load_config(_write(tmp_path, broken))

    def test_studio_and_atypical_are_accepted_dispositions(self, tmp_path):
        config = copy.deepcopy(VALID)
        config["profiles"]["p"]["search"]["dispositions"] = ["garsoniéra", "atypický"]
        loaded = load_config(_write(tmp_path, config))
        assert loaded["profiles"]["p"]["search"]["dispositions"] == ["garsoniéra", "atypický"]

    def test_invalid_offer_type_is_rejected(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(offer_type="lease"))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search\.offer_type"):
            load_config(_write(tmp_path, broken))
