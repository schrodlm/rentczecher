"""Tests for offline geocoding: candidate extraction and gazetteer resolution.

Resolution tests run against the real bundled gazetteer, so they pin what a
user's install actually answers for the location strings the portals emit.

Run: python3 -m pytest tests/test_geocoding.py -v
"""

import pytest

from rentczecher.adapters.geocoding.gazetteer import Gazetteer, candidate_names


class TestCandidateNames:
    def test_splits_commas_and_city_part_dashes(self):
        assert candidate_names("U Vody, Praha - Holešovice, Praha 7") == [
            "u vody", "praha", "holesovice", "praha 7"]

    def test_house_numbers_yield_a_stripped_variant(self):
        names = candidate_names("Škarmanská 369 / 369, Domažlice")
        assert "skarmanska" in names
        assert "domazlice" in names

    def test_district_number_yields_bare_city_variant(self):
        assert candidate_names("Praha 7") == ["praha 7", "praha"]

    def test_kraj_segments_are_discarded(self):
        assert candidate_names("Domažlice, Plzeňský kraj") == ["domazlice"]

    def test_diacritics_and_case_are_normalized(self):
        assert candidate_names("VELETRŽNÍ") == ["veletrzni"]

    def test_duplicates_collapse(self):
        assert candidate_names("Praha, Praha") == ["praha"]

    def test_empty_string_yields_nothing(self):
        assert candidate_names("") == []


@pytest.fixture(scope="module")
def gazetteer():
    return Gazetteer()


class TestResolve:
    """Portal-shaped location strings against the shipped gazetteer."""

    def test_sreality_street_city_part_district(self, gazetteer):
        # 'U Vody' exists in 12 municipalities; 'Praha' must disambiguate.
        # The registry's official spelling is 'U vody', unlike the portal's.
        place = gazetteer.resolve("U Vody, Praha - Holešovice, Praha 7")
        assert place.tier == "street"
        assert place.name == "U vody"
        assert place.muni_name == "Praha"

    def test_bezrealitky_street_and_district(self, gazetteer):
        # 'Veletržní' also exists in Brno; the bare-city variant of
        # 'Praha 7' must carry the municipality agreement.
        place = gazetteer.resolve("Veletržní, Praha 7")
        assert place.tier == "street"
        assert place.muni_name == "Praha"
        assert abs(place.lat - 50.10) < 0.02
        assert abs(place.lon - 14.43) < 0.02

    def test_bezrealitky_street_with_part_label(self, gazetteer):
        # 'U Studánky' exists 49 times countrywide.
        place = gazetteer.resolve("U Studánky, Praha - Bubeneč")
        assert place.tier == "street"
        assert place.muni_name == "Praha"

    def test_remax_unique_street_overrides_district_label(self, gazetteer):
        # RE/MAX writes the district ('Domažlice') where the municipality
        # belongs; the street is in Kdyně and is unique countrywide.
        place = gazetteer.resolve("Škarmanská 369 / 369, Domažlice , Plzeňský kraj")
        assert place.tier == "street"
        assert place.muni_name == "Kdyně"
        assert abs(place.lat - 49.396) < 0.01

    def test_remax_municipality_with_part(self, gazetteer):
        place = gazetteer.resolve("Domažlice - Týnské Předměstí")
        assert place.tier == "municipality_part"
        assert place.name == "Týnské Předměstí"
        assert place.muni_name == "Domažlice"

    def test_remax_municipality_only(self, gazetteer):
        place = gazetteer.resolve("Domažlice , Plzeňský kraj")
        assert place.tier == "municipality"
        assert place.name == "Domažlice"

    def test_bare_city_district(self, gazetteer):
        place = gazetteer.resolve("Praha 7")
        assert place.tier == "city_district"
        assert place.muni_name == "Praha"

    def test_ambiguous_municipality_resolves_to_none(self, gazetteer):
        # 14 municipalities are named Nová Ves (plus an Ostrava city
        # district); guessing one would put a property in the wrong corner
        # of the country.
        assert gazetteer.resolve("Nová Ves") is None

    def test_ambiguous_part_across_municipalities_resolves_to_none(self, gazetteer):
        # A part named Holešovice exists in Praha and in Chroustovice.
        assert gazetteer.resolve("Holešovice") is None

    def test_town_with_self_named_part_resolves(self, gazetteer):
        # Kdyně the municipality contains a part also named Kdyně; one
        # municipality at two tiers is one place, not an ambiguity.
        place = gazetteer.resolve("Kdyně")
        assert place is not None
        assert place.muni_name == "Kdyně"

    def test_bare_capital_resolves(self, gazetteer):
        place = gazetteer.resolve("Praha")
        assert place.tier == "municipality"
        assert place.name == "Praha"

    def test_garbage_resolves_to_none(self, gazetteer):
        assert gazetteer.resolve("!!!") is None

    def test_kraj_only_resolves_to_none(self, gazetteer):
        assert gazetteer.resolve("Plzeňský kraj") is None


class TestResolveDistrictLabeled:
    """RE/MAX-shaped strings: the municipality slot holds the okres."""

    def test_unique_street_in_the_okres_resolves(self, gazetteer):
        place = gazetteer.resolve("Škarmanská 369 / 369, Domažlice , Plzeňský kraj",
                                  district_labeled=True)
        assert place.tier == "street"
        assert place.muni_name == "Kdyně"
        assert place.okres_name == "Domažlice"

    def test_repeated_street_in_the_okres_degrades_to_district(self, gazetteer):
        # Nádražní exists in Klatovy town AND elsewhere in okres Klatovy;
        # picking the town's street would sit ~25 km wrong at full
        # confidence. The honest answer is the district.
        place = gazetteer.resolve("Nádražní 10, Klatovy, Plzeňský kraj",
                                  district_labeled=True)
        assert place.tier == "district"
        assert place.name == "Klatovy"

    def test_bare_okres_resolves_to_the_district(self, gazetteer):
        place = gazetteer.resolve("Domažlice , Plzeňský kraj", district_labeled=True)
        assert place.tier == "district"
        assert place.name == "Domažlice"

    def test_okres_only_name_resolves_to_the_district(self, gazetteer):
        place = gazetteer.resolve("Brno-venkov, Jihomoravský kraj", district_labeled=True)
        assert place.tier == "district"
        assert place.name == "Brno-venkov"

    def test_non_district_town_still_resolves_as_town(self, gazetteer):
        # A name that is not an okres keeps normal town resolution even
        # under the district label.
        place = gazetteer.resolve("Kdyně, Plzeňský kraj", district_labeled=True)
        assert place.muni_name == "Kdyně"
        assert place.tier != "district"


class TestResolveDefaultKeepsTownSemantics:
    def test_street_plus_capital_name_means_the_town(self, gazetteer):
        # Sreality/Bezrealitky write the municipality, so 'Klatovy' vouches
        # for the town's own street.
        place = gazetteer.resolve("Nádražní 10, Klatovy")
        assert place.tier == "street"
        assert place.muni_name == "Klatovy"

    def test_okres_scope_rescues_a_street_missing_from_the_named_town(self, gazetteer):
        # Default mode also uses the okres scope when town agreement finds
        # nothing: the only Škarmanská in okres Domažlice is in Kdyně.
        place = gazetteer.resolve("Škarmanská 369 / 369, Domažlice , Plzeňský kraj")
        assert place.tier == "street"
        assert place.muni_name == "Kdyně"

    def test_resolved_places_carry_the_okres(self, gazetteer):
        place = gazetteer.resolve("Kdyně")
        assert place.okres_name == "Domažlice"


class TestReadOnly:
    def test_missing_gazetteer_fails_loudly(self, tmp_path):
        import sqlite3
        with pytest.raises(sqlite3.OperationalError):
            Gazetteer(db_path=tmp_path / "missing.sqlite")
