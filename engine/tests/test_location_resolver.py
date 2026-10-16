"""Tests for the place resolver over the gazetteer's portal tables.

Run: python3 -m pytest tests/test_location_resolver.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher_engine.domain.errors import PlaceNotFoundError
from rentczecher_engine.domain.location import PlaceRef


class TestResolveDistricts:
    """A district yields its per-portal search parameters from the shipped
    table."""

    def test_praha_7_resolves_to_production_proven_params(self):
        params = resolve(PlaceRef("obvod", 78))
        assert params.sreality_district_id == 5007
        assert params.remax_regions == {19: (78,)}
        assert params.bezrealitky_region_id == "R20000064250"
        assert params.name == "Praha 7"

    def test_domazlice_resolves_to_production_proven_params(self):
        params = resolve(PlaceRef("okres", 3401))
        assert params.sreality_district_id == 8
        assert params.sreality_region_id == 2
        assert params.remax_regions == {43: (3401,)}
        assert params.bezrealitky_region_id == "R441864"


class TestResolveRegions:
    """A kraj resolves to a region-level search: no sreality district id,
    every remax district of the kraj, the kraj's bezrealitky id."""

    def test_plzensky_kraj_resolves_region_wide(self):
        params = resolve(PlaceRef("kraj", 43))
        assert params.sreality_district_id is None
        assert params.sreality_region_id == 2
        (region_id, district_ids), = params.remax_regions.items()
        assert region_id == 43
        assert len(district_ids) == 7
        assert 3401 in district_ids
        assert params.bezrealitky_region_id.startswith("R")

    def test_praha_region_uses_the_frontend_verified_id(self):
        params = resolve(PlaceRef("kraj", 19))
        assert params.sreality_district_id is None
        assert params.sreality_region_id == 10
        assert params.bezrealitky_region_id == "R435541"
        assert len(params.remax_regions[19]) == 10


class TestResolveSmallerPlaces:
    """A place smaller than any portal searches resolves to the parameters
    of its search area."""

    def test_a_town_searches_its_okres(self):
        assert resolve(PlaceRef("obec", 553786)) == resolve(PlaceRef("okres", 3401))

    def test_a_prague_street_searches_its_obvod(self):
        assert resolve(PlaceRef("ulice", 467103)) == resolve(PlaceRef("obvod", 78))

    def test_praha_searches_its_kraj(self):
        assert resolve(PlaceRef("obec", 554782)) == resolve(PlaceRef("kraj", 19))


class TestResolveFailure:
    """An unknown place fails loudly."""

    def test_unknown_place_raises(self):
        with pytest.raises(PlaceNotFoundError):
            resolve(PlaceRef("okres", 999999))

    def test_an_unknown_place_smaller_than_a_district_raises(self):
        with pytest.raises(PlaceNotFoundError):
            resolve(PlaceRef("obec", 999999999))

    def test_every_search_place_resolves_by_its_kind_and_code(self):
        """Each kraj, okres and obvod in the gazetteer is a search place."""
        from rentczecher_engine.adapters.geocoding.gazetteer import open_gazetteer
        conn = open_gazetteer()
        stmt = """
            SELECT 'kraj' AS kind, code, name FROM kraje
            UNION ALL SELECT 'okres', code, name FROM okresy
            UNION ALL SELECT 'obvod', code, name FROM obvody
        """
        rows = conn.execute(stmt).fetchall()
        conn.close()
        assert len(rows) == 100
        for row in rows:
            assert resolve(PlaceRef(row["kind"], row["code"])).name == row["name"]


class TestPlaceParamsImmutability:
    def test_fields_cannot_be_reassigned(self):
        params = resolve(PlaceRef("obvod", 78))
        with pytest.raises(dataclasses.FrozenInstanceError):
            params.name = "other"  # type: ignore[misc]

    def test_params_type_is_shared(self):
        assert isinstance(resolve(PlaceRef("obvod", 78)), PlaceParams)
