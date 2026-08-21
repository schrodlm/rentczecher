"""Tests for offline geocoding: candidate normalization and gazetteer resolution.

Resolution tests run against the real bundled gazetteer, so they pin what a
user's install actually answers for the place names the scrapers emit.

Run: python3 -m pytest tests/test_geocoding.py -v
"""

import pytest

from rentczecher.adapters.geocoding.gazetteer import Gazetteer, candidate_names
from rentczecher.domain.location import ParsedPlace


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
        place = gazetteer.resolve(ParsedPlace(names=("U Vody", "Praha", "Holešovice", "Praha 7")))
        assert place.tier == "street"
        assert place.name == "U vody"
        assert place.muni_name == "Praha"

    def test_street_with_city_district(self, gazetteer):
        # 'Veletržní' also exists in Brno; the bare-city variant of
        # 'Praha 7' must carry the municipality agreement.
        place = gazetteer.resolve(ParsedPlace(names=("Veletržní", "Praha 7")))
        assert place.tier == "street"
        assert place.muni_name == "Praha"
        assert abs(place.lat - 50.10) < 0.02
        assert abs(place.lon - 14.43) < 0.02

    def test_street_repeated_across_the_country(self, gazetteer):
        # 'U Studánky' exists 49 times countrywide.
        place = gazetteer.resolve(ParsedPlace(names=("U Studánky", "Praha", "Bubeneč")))
        assert place.tier == "street"
        assert place.muni_name == "Praha"

    def test_okres_scope_rescues_a_street_missing_from_the_named_town(self, gazetteer):
        # No town named Domažlice has a Škarmanská; the okres of the same
        # name contains exactly one, in Kdyně.
        place = gazetteer.resolve(ParsedPlace(names=("Škarmanská 369 / 369", "Domažlice")))
        assert place.tier == "street"
        assert place.muni_name == "Kdyně"
        assert abs(place.lat - 49.396) < 0.01

    def test_street_plus_town_means_the_town(self, gazetteer):
        # Sreality/Bezrealitky name the municipality, and it vouches for
        # its own street.
        place = gazetteer.resolve(ParsedPlace(names=("Nádražní 10", "Klatovy")))
        assert place.tier == "street"
        assert place.muni_name == "Klatovy"

    def test_bare_municipality(self, gazetteer):
        place = gazetteer.resolve(ParsedPlace(names=("Domažlice",)))
        assert place.tier == "municipality"
        assert place.name == "Domažlice"

    def test_bare_city_district(self, gazetteer):
        place = gazetteer.resolve(ParsedPlace(names=("Praha 7",)))
        assert place.tier == "city_district"
        assert place.muni_name == "Praha"

    def test_bare_capital_resolves(self, gazetteer):
        place = gazetteer.resolve(ParsedPlace(names=("Praha",)))
        assert place.tier == "municipality"
        assert place.name == "Praha"

    def test_town_with_self_named_part_resolves(self, gazetteer):
        # Kdyně the municipality contains a part also named Kdyně; one
        # municipality at two tiers is one place, not an ambiguity.
        place = gazetteer.resolve(ParsedPlace(names=("Kdyně",)))
        assert place is not None
        assert place.muni_name == "Kdyně"

    def test_resolved_places_carry_the_okres(self, gazetteer):
        place = gazetteer.resolve(ParsedPlace(names=("Kdyně",)))
        assert place.okres_name == "Domažlice"

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
        place = gazetteer.resolve(
            ParsedPlace(names=("Škarmanská 369 / 369",), district="Domažlice"))
        assert place.tier == "street"
        assert place.muni_name == "Kdyně"
        assert place.okres_name == "Domažlice"

    def test_repeated_street_in_the_okres_degrades_to_district(self, gazetteer):
        # Nádražní exists in Klatovy town AND elsewhere in okres Klatovy;
        # picking the town's street would sit ~25 km wrong at full
        # confidence. The honest answer is the district.
        place = gazetteer.resolve(ParsedPlace(names=("Nádražní 10",), district="Klatovy"))
        assert place.tier == "district"
        assert place.name == "Klatovy"

    def test_bare_okres_resolves_to_the_district(self, gazetteer):
        place = gazetteer.resolve(ParsedPlace(district="Domažlice"))
        assert place.tier == "district"
        assert place.name == "Domažlice"

    def test_okres_only_name_resolves_to_the_district(self, gazetteer):
        place = gazetteer.resolve(ParsedPlace(district="Brno-venkov"))
        assert place.tier == "district"
        assert place.name == "Brno-venkov"

    def test_town_evidence_upgrades_the_district_fallback(self, gazetteer):
        # Five towns in okres Cheb have a Dlouhá; the town name in the pool
        # picks one at street tier where the district alone could only
        # answer coarsely.
        place = gazetteer.resolve(ParsedPlace(
            names=("Dlouhá 2534 / 2534", "Aš"), district="Cheb"))
        assert place.tier == "street"
        assert place.muni_name == "Aš"

    def test_stated_district_that_is_no_district_resolves_to_none(self, gazetteer):
        # Kdyně is a town, not an okres; a statement the data refutes means
        # the caller's split cannot be trusted at all.
        assert gazetteer.resolve(ParsedPlace(district="Kdyně")) is None


class TestNameTiers:
    def test_ambiguous_street_name_still_reports_street_tier(self, gazetteer):
        assert "street" in gazetteer.name_tiers("Veletržní")

    def test_capital_name_reports_all_its_tiers(self, gazetteer):
        tiers = gazetteer.name_tiers("Klatovy")
        assert "municipality" in tiers
        assert "district" in tiers

    def test_unknown_name_reports_nothing(self, gazetteer):
        assert gazetteer.name_tiers("!!!") == frozenset()

    def test_municipality_scope_drops_other_municipalities_readings(self, gazetteer):
        assert "street" in gazetteer.name_tiers("Bubeneč")
        assert gazetteer.name_tiers("Bubeneč", muni="Praha") == frozenset({"municipality_part"})

    def test_municipality_scope_keeps_the_local_reading(self, gazetteer):
        assert gazetteer.name_tiers("Bubeneč", muni="Lenešice") == frozenset({"street"})

    def test_municipality_scope_with_no_local_bearer_reports_nothing(self, gazetteer):
        assert gazetteer.name_tiers("U studánky", muni="Lenešice") == frozenset()


class TestReverse:
    def test_point_reverse_geocodes_to_its_part(self, gazetteer):
        place = gazetteer.reverse(50.1, 14.43)
        assert place.muni_name == "Praha"
        assert place.tier in ("municipality_part", "municipality")

    def test_point_outside_czechia_is_none(self, gazetteer):
        assert gazetteer.reverse(40.0, 10.0) is None


class TestReadOnly:
    def test_missing_gazetteer_fails_loudly(self, tmp_path):
        import sqlite3
        with pytest.raises(sqlite3.OperationalError):
            Gazetteer(db_path=tmp_path / "missing.sqlite")
