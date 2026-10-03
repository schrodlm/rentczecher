"""Tests for offline geocoding: candidate normalization and gazetteer resolution.

Resolution tests run against the real bundled gazetteer, so they pin what a
user's install actually answers for the place names the scrapers emit.

Run: python3 -m pytest tests/test_geocoding.py -v
"""

import pytest

from rentczecher_engine.adapters.geocoding.gazetteer import (
    Gazetteer,
    candidate_names,
    normalize_name,
    open_gazetteer,
)
from rentczecher_engine.domain.location import ParsedPlace


class TestNormalizeName:
    """One key for all portals' (and users') spellings of the same place."""

    @pytest.mark.parametrize("variants, expected", [
        (("Domažlice", "okres Domažlice"), "domazlice"),
        (("Plzeňský kraj", "Plzeňský"), "plzensky"),
        (("Hlavní město Praha", "Praha"), "praha"),
        (("Kraj Vysočina", "Vysočina"), "vysocina"),
        (("Praha 7",), "praha 7"),
        (("Praha-východ", "okres Praha-východ"), "praha-vychod"),
        (("Brno-město",), "brno-mesto"),
    ])
    def test_portal_spellings_normalize_identically(self, variants, expected):
        for variant in variants:
            assert normalize_name(variant) == expected, variant


class TestCandidateNames:
    def test_house_numbers_yield_a_stripped_variant(self):
        assert candidate_names(["Škarmanská 369 / 369"]) == [
            "skarmanska 369 / 369", "skarmanska"]

    def test_district_number_yields_bare_city_variant(self):
        assert candidate_names(["Praha 7"]) == ["praha 7", "praha"]

    def test_diacritics_and_case_are_normalized(self):
        assert candidate_names(["VELETRŽNÍ"]) == ["veletrzni"]

    def test_duplicates_collapse(self):
        assert candidate_names(["Praha", "Praha"]) == ["praha"]

    def test_empty_names_yield_nothing(self):
        assert candidate_names(["", "  "]) == []


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


class TestResolve:
    """Scraper-split place names against the shipped gazetteer."""

    def test_street_with_city_and_part(self, gazetteer):
        # 'U Vody' exists in 12 municipalities; 'Praha' must disambiguate.
        # The registry's official spelling is 'U vody', unlike the portal's.
        location = gazetteer.resolve(ParsedPlace(names=("U Vody", "Praha", "Holešovice", "Praha 7")))
        assert location.most_specific()[0] == "ulice"
        assert location.ulice.name == "U vody"
        assert location.obec.name == "Praha"

    def test_street_with_city_district(self, gazetteer):
        # 'Veletržní' also exists in Brno; the bare-city variant of
        # 'Praha 7' must carry the municipality agreement.
        location = gazetteer.resolve(ParsedPlace(names=("Veletržní", "Praha 7")))
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Praha"
        assert abs(location.ulice.lat - 50.10) < 0.02
        assert abs(location.ulice.lon - 14.43) < 0.02

    def test_street_repeated_across_the_country(self, gazetteer):
        # 'U Studánky' exists 49 times countrywide.
        location = gazetteer.resolve(ParsedPlace(names=("U Studánky", "Praha", "Bubeneč")))
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Praha"

    def test_okres_scope_rescues_a_street_missing_from_the_named_town(self, gazetteer):
        # No town named Domažlice has a Škarmanská; the okres of the same
        # name contains exactly one, in Kdyně.
        location = gazetteer.resolve(ParsedPlace(names=("Škarmanská 369 / 369", "Domažlice")))
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Kdyně"
        assert abs(location.ulice.lat - 49.396) < 0.01

    def test_street_plus_town_means_the_town(self, gazetteer):
        # Sreality/Bezrealitky name the municipality, and it vouches for
        # its own street.
        location = gazetteer.resolve(ParsedPlace(names=("Nádražní 10", "Klatovy")))
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Klatovy"

    def test_bare_municipality(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Domažlice",)))
        assert location.most_specific()[0] == "obec"
        assert location.obec.name == "Domažlice"

    def test_bare_city_district(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Praha 7",)))
        assert location.most_specific()[0] == "mestska_cast"
        assert location.obec.name == "Praha"

    def test_bare_capital_resolves(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Praha",)))
        assert location.most_specific()[0] == "obec"
        assert location.obec.name == "Praha"

    def test_a_bare_town_name_resolves_to_the_town_not_its_central_part(self, gazetteer):
        # Kdyně the municipality contains a part also named Kdyně; one
        # municipality at two tiers is one place, not an ambiguity.
        location = gazetteer.resolve(ParsedPlace(names=("Kdyně",)))
        assert location.obec.name == "Kdyně"
        assert location.cast_obce is None

    def test_ambiguous_municipality_resolves_to_none(self, gazetteer):
        # 14 municipalities are named Nová Ves (plus an Ostrava city
        # district); guessing one would put a property in the wrong corner
        # of the country.
        assert gazetteer.resolve(ParsedPlace(names=("Nová Ves",))) is None

    def test_ambiguous_part_across_municipalities_resolves_to_none(self, gazetteer):
        # A part named Holešovice exists in Praha and in Chroustovice.
        assert gazetteer.resolve(ParsedPlace(names=("Holešovice",))) is None

    def test_garbage_resolves_to_none(self, gazetteer):
        assert gazetteer.resolve(ParsedPlace(names=("!!!",))) is None

    def test_no_names_resolve_to_none(self, gazetteer):
        assert gazetteer.resolve(ParsedPlace()) is None


class TestResolveStatedDistrict:
    """Names with the okres passed separately, as the RE/MAX scraper splits
    them: the stated name resolves only as a district."""

    def test_unique_street_in_the_okres_resolves(self, gazetteer):
        location = gazetteer.resolve(
            ParsedPlace(names=("Škarmanská 369 / 369",), district="Domažlice"))
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Kdyně"
        assert location.okres.name == "Domažlice"

    def test_repeated_street_in_the_okres_degrades_to_district(self, gazetteer):
        # Nádražní exists in Klatovy town AND elsewhere in okres Klatovy;
        # picking the town's street would sit ~25 km wrong at full
        # confidence. The honest answer is the district.
        location = gazetteer.resolve(ParsedPlace(names=("Nádražní 10",), district="Klatovy"))
        assert location.most_specific()[0] == "okres"
        assert location.okres.name == "Klatovy"

    def test_bare_okres_resolves_to_the_district(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(district="Domažlice"))
        assert location.most_specific()[0] == "okres"
        assert location.okres.name == "Domažlice"

    def test_okres_only_name_resolves_to_the_district(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(district="Brno-venkov"))
        assert location.most_specific()[0] == "okres"
        assert location.okres.name == "Brno-venkov"

    def test_town_evidence_upgrades_the_district_fallback(self, gazetteer):
        # Five towns in okres Cheb have a Dlouhá; the town name in the pool
        # picks one at street tier where the district alone could only
        # answer coarsely.
        location = gazetteer.resolve(ParsedPlace(
            names=("Dlouhá 2534 / 2534", "Aš"), district="Cheb"))
        assert location.most_specific()[0] == "ulice"
        assert location.obec.name == "Aš"

    def test_stated_district_that_is_no_district_resolves_to_none(self, gazetteer):
        # Kdyně is a town, not an okres; a statement the data refutes means
        # the caller's split cannot be trusted at all.
        assert gazetteer.resolve(ParsedPlace(district="Kdyně")) is None


class TestResolveParents:
    """A resolved location carries the strict parents of its unit."""

    def test_an_obec_carries_its_okres_and_kraj(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Domažlice",)))
        assert location.okres.name == "Domažlice"
        assert location.kraj.name == "Plzeňský kraj"

    def test_praha_lies_in_its_kraj_and_no_okres(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Praha",)))
        assert location.obec.name == "Praha"
        assert location.okres is None
        assert location.kraj.name == "Hlavní město Praha"

    def test_a_prague_mestska_cast_carries_its_obvod(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Praha-Troja",)))
        assert location.mestska_cast.name == "Praha-Troja"
        assert location.obvod.name == "Praha 7"

    def test_a_mestska_cast_outside_praha_has_no_obvod(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Brno-Královo Pole",)))
        assert location.mestska_cast.name == "Brno-Královo Pole"
        assert location.obvod is None
        assert location.obec.name == "Brno"

    def test_an_okres_carries_its_kraj_and_no_obec(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(district="Domažlice"))
        assert location.kraj.name == "Plzeňský kraj"
        assert location.obec is None


class TestResolveFillsNamedUnits:
    """Each name the text gives besides the resolved unit, looked up inside
    that unit's obec, fills its kind when exactly one unit there matches."""

    def test_the_other_names_fill_the_cast_obce_and_obvod(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Přístavní", "Praha", "Holešovice", "Praha 7")))
        assert location.ulice.name == "Přístavní"
        assert location.cast_obce.name == "Holešovice"
        assert location.obvod.name == "Praha 7"
        assert location.mestska_cast is None

    def test_a_named_mestska_cast_brings_its_obvod(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Trojská", "Praha", "Praha-Troja")))
        assert location.mestska_cast.name == "Praha-Troja"
        assert location.obvod.name == "Praha 7"

    def test_a_name_outside_the_obec_fills_nothing(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Přístavní", "Praha", "Kdyně")))
        assert location.cast_obce is None
        assert location.mestska_cast is None

    def test_the_obec_name_never_fills_its_same_named_part_even_with_a_number(self, gazetteer):
        # Kdyně has a část obce named Kdyně.
        location = gazetteer.resolve(ParsedPlace(names=("Škarmanská 369", "Kdyně 369")))
        assert location.ulice.name == "Škarmanská"
        assert location.cast_obce is None

    def test_the_okres_name_never_fills_a_same_named_part(self, gazetteer):
        # Brno has a část obce named like its okres, Brno-město.
        location = gazetteer.resolve(ParsedPlace(names=("Veveří", "Brno", "Brno-město")))
        assert location.okres.name == "Brno-město"
        assert location.cast_obce is None

    def test_two_names_stating_different_obvody_leave_the_obvod_open(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("Veletržní", "Praha 6", "Praha 7")))
        assert location.ulice.name == "Veletržní"
        assert location.obvod is None


class TestResolveHouseNumbers:
    def test_the_house_numbers_ride_along_as_written(self, gazetteer):
        place = ParsedPlace(names=("U Vody", "Praha"), cislo_popisne="1401", cislo_orientacni="5a")
        location = gazetteer.resolve(place)
        assert location.cislo_popisne == "1401"
        assert location.cislo_orientacni == "5a"

    def test_a_location_without_house_numbers_leaves_them_open(self, gazetteer):
        location = gazetteer.resolve(ParsedPlace(names=("U Vody", "Praha")))
        assert location.cislo_popisne is None
        assert location.cislo_orientacni is None


class TestNameTiers:
    def test_ambiguous_street_name_still_reports_street_tier(self, gazetteer):
        assert "ulice" in gazetteer.name_tiers("Veletržní")

    def test_capital_name_reports_all_its_tiers(self, gazetteer):
        tiers = gazetteer.name_tiers("Klatovy")
        assert "obec" in tiers
        assert "okres" in tiers

    def test_unknown_name_reports_nothing(self, gazetteer):
        assert gazetteer.name_tiers("!!!") == frozenset()

    def test_municipality_scope_drops_other_municipalities_readings(self, gazetteer):
        assert "ulice" in gazetteer.name_tiers("Bubeneč")
        assert gazetteer.name_tiers("Bubeneč", muni="Praha") == frozenset({"cast_obce"})

    def test_municipality_scope_keeps_the_local_reading(self, gazetteer):
        assert gazetteer.name_tiers("Bubeneč", muni="Lenešice") == frozenset({"ulice"})

    def test_municipality_scope_with_no_local_bearer_reports_nothing(self, gazetteer):
        assert gazetteer.name_tiers("U studánky", muni="Lenešice") == frozenset()


class TestRuianCode:
    def test_a_resolved_unit_carries_its_ruian_code(self, gazetteer):
        """The code is the one the gazetteer stores for that street."""
        location = gazetteer.resolve(ParsedPlace(names=("Veletržní", "Praha")))
        conn = open_gazetteer()
        stmt = "SELECT u.code FROM ulice u JOIN obce o ON o.code = u.obec_code WHERE u.name = 'Veletržní' AND o.name = 'Praha'"
        assert location.ulice.code == conn.execute(stmt).fetchone()["code"]
        conn.close()


class TestSchemaVersion:
    def test_a_gazetteer_built_for_another_schema_is_refused(self, tmp_path):
        """A stale file fails at open with a hint, not later with missing columns."""
        import shutil
        import sqlite3
        from importlib.resources import files
        stale = tmp_path / "gazetteer.sqlite"
        shutil.copyfile(str(files("rentczecher_engine.adapters.geocoding") / "gazetteer.sqlite"), stale)
        conn = sqlite3.connect(stale)
        conn.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")
        conn.commit()
        conn.close()
        with pytest.raises(RuntimeError, match="rebuild it"):
            Gazetteer(db_path=stale)


class TestReadOnly:
    def test_missing_gazetteer_fails_loudly(self, tmp_path):
        import sqlite3
        with pytest.raises(sqlite3.OperationalError):
            Gazetteer(db_path=tmp_path / "missing.sqlite")
