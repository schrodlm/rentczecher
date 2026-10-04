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
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria, Preferences
from tests.profiles import criteria, layouts, preferences, profile

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
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
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

    def test_the_kind_is_read_in_any_case(self, tmp_path):
        written = _broken(lambda c: c["profiles"]["p"]["search"].update(place="Obvod Praha 7"))
        (loaded,) = load_config(_write(tmp_path, written))
        assert loaded.criteria.place == PlaceRef(kind="obvod", code=78)

    @pytest.mark.parametrize("place", ["obec Kdyně", "Praha 7"])
    def test_a_place_not_written_as_a_searchable_kind_is_rejected(self, tmp_path, place):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(place=place))
        with pytest.raises(ConfigError, match="name a kraj, okres or obvod"):
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

    def test_unset_search_settings_load_as_unbounded(self, tmp_path):
        (loaded,) = load_config(_write(tmp_path, VALID))
        assert loaded.criteria == Criteria(
            offer_type="rent", estate_type="flat", place=PlaceRef(kind="obvod", code=78), max_price=25000)

    def test_each_profile_loads_as_a_profile_in_file_order(self, tmp_path):
        """Profiles keep the order the file lists them in. A profile's key
        becomes its id, its scrapers its portals, and its name and enabled
        flag carry over."""
        written = _broken(lambda c: c["profiles"].update(a={
            **VALID["profiles"]["p"], "name": "A", "enabled": False, "scrapers": ["remax", "bezrealitky"]}))
        assert load_config(_write(tmp_path, written)) == [
            profile(criteria=criteria(max_price=25000)),
            profile(id="a", name="A", enabled=False, portals=("remax", "bezrealitky"),
                    criteria=criteria(max_price=25000)),
        ]

    def test_search_loads_as_criteria(self, tmp_path):
        """Every search setting lands in its own criterion."""
        written = _broken(lambda c: c["profiles"]["p"].update(search={
            "offer_type": "sale", "estate_type": "house", "place": "okres Domažlice",
            "min_price": 1000000, "max_price": 5000000, "min_size_m2": 80, "min_land_m2": 600,
            "min_rooms": 4, "max_rooms": 5, "kitchen": "separate"}))
        (loaded,) = load_config(_write(tmp_path, written))
        assert loaded.criteria == Criteria(
            offer_type="sale", estate_type="house", place=PlaceRef(kind="okres", code=3401),
            min_price=1000000, max_price=5000000, min_size_m2=80, min_land_m2=600,
            min_rooms=4, max_rooms=5, kitchen="separate")

    @pytest.mark.parametrize("bound", ["min_rooms", "max_rooms"])
    @pytest.mark.parametrize("rooms", [0, 10])
    def test_a_room_count_outside_one_to_nine_is_rejected(self, tmp_path, bound, rooms):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update({bound: rooms}))
        with pytest.raises(ConfigError, match=rf"profiles\.p\.search: {bound} must be 1 to 9"):
            load_config(_write(tmp_path, broken))

    @pytest.mark.parametrize("rooms", [1, 9])
    def test_a_range_of_one_room_count_at_either_end_loads(self, tmp_path, rooms):
        written = _broken(lambda c: c["profiles"]["p"]["search"].update(min_rooms=rooms, max_rooms=rooms))
        (loaded,) = load_config(_write(tmp_path, written))
        assert (loaded.criteria.min_rooms, loaded.criteria.max_rooms) == (rooms, rooms)

    def test_a_room_range_running_backwards_is_rejected(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(min_rooms=3, max_rooms=2))
        with pytest.raises(ConfigError, match="min_rooms must not exceed max_rooms"):
            load_config(_write(tmp_path, broken))

    def test_an_unknown_kitchen_kind_is_rejected(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(kitchen="none"))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search\.kitchen"):
            load_config(_write(tmp_path, broken))

    def test_scoring_loads_as_preferences_with_layouts_parsed(self, tmp_path):
        """Every scoring setting lands in its own preference, preferred
        dispositions arrive parsed and preferred places resolved, each in their
        order of preference."""
        written = _broken(lambda c: c["profiles"]["p"].update(scoring={
            "price_per_m2_weight": 10, "disposition_weight": 20,
            "preferred_dispositions": ["2+kk", "garsoniéra"],
            "size_weight": 30, "ideal_size_m2": 60,
            "place_weight": 40, "preferred_places": ["cast_obce Bubeneč", "cast_obce Vinohrady"],
            "land_weight": 50, "ideal_land_m2": 900,
            "price_weight": 60, "max_good_price": 4000000}))
        (loaded,) = load_config(_write(tmp_path, written))
        assert loaded.preferences == Preferences(
            price_per_m2_weight=10, disposition_weight=20,
            preferred_dispositions=layouts("2+kk", "1+kk"),
            size_weight=30, ideal_size_m2=60,
            place_weight=40, preferred_places=(PlaceRef("cast_obce", 490024), PlaceRef("cast_obce", 490229)),
            land_weight=50, ideal_land_m2=900,
            price_weight=60, max_good_price=4000000)

    def test_an_absent_scoring_section_loads_as_no_preferences(self, tmp_path):
        """Every weight is off and every setting is left empty."""
        (loaded,) = load_config(_write(tmp_path, VALID))
        assert loaded.preferences == preferences()

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
            max_prise=25000))
        with pytest.raises(ConfigError, match=r"max_prise: unknown key \(did you mean 'max_price'\?\)"):
            load_config(_write(tmp_path, broken))

    def test_unknown_scraper_name_is_an_error(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["scrapers"].append("idnes"))
        with pytest.raises(ConfigError, match="unknown scraper 'idnes'"):
            load_config(_write(tmp_path, broken))

    def test_unparseable_preferred_disposition_is_named(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"].update(
            scoring={"disposition_weight": 30, "preferred_dispositions": ["Rodinný"]}))
        with pytest.raises(ConfigError,
                           match=r"profiles\.p\.scoring\.preferred_dispositions.*not a disposition: Rodinný"):
            load_config(_write(tmp_path, broken))

    @pytest.mark.parametrize(("written", "message"), [
        ("Bubeneč", "start 'Bubeneč' with its kind"),
        ("cast_obce Bubenec Dolni", "unknown place"),
        ("cast_obce Holešovice", "several places are called"),
    ])
    def test_a_preferred_place_that_names_no_one_place_is_rejected(self, tmp_path, written, message):
        broken = _broken(lambda c: c["profiles"]["p"].update(
            scoring={"place_weight": 15, "preferred_places": [written]}))
        with pytest.raises(ConfigError, match=rf"profiles\.p\.scoring\.preferred_places: .*{message}"):
            load_config(_write(tmp_path, broken))

    def test_a_zero_bound_is_rejected_naming_the_field(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(min_price=0))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search: min_price must be positive"):
            load_config(_write(tmp_path, broken))

    def test_a_weighted_preference_without_its_setting_names_the_field(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"].update(scoring={"size_weight": 15}))
        with pytest.raises(ConfigError, match=r"profiles\.p\.scoring: size_weight needs a positive ideal_size_m2"):
            load_config(_write(tmp_path, broken))

    def test_invalid_offer_type_is_rejected(self, tmp_path):
        broken = _broken(lambda c: c["profiles"]["p"]["search"].update(offer_type="lease"))
        with pytest.raises(ConfigError, match=r"profiles\.p\.search\.offer_type"):
            load_config(_write(tmp_path, broken))
