"""Tests for the place resolver over the gazetteer's portal tables.

Run: python3 -m pytest tests/test_location_resolver.py -v
"""

import dataclasses

import pytest

from rentczecher_engine.adapters.scrapers.location_resolver import (
    PlaceParams,
    resolve,
    slugify,
)
from rentczecher_engine.domain.errors import PlaceNotFoundError


class TestSlugify:
    def test_slugify_replaces_spaces(self):
        assert slugify("Praha 7") == "praha-7"
        assert slugify("Hlavní město Praha") == "praha"


class TestResolveDistricts:
    """A district slug or free-text name yields that district's per-portal
    search parameters from the shipped table."""

    def test_praha_7_resolves_to_production_proven_params(self):
        params = resolve("praha-7")
        assert params.sreality_district_id == 5007
        assert params.remax_regions == {19: (78,)}
        assert params.bezrealitky_region_id == "R20000064250"
        assert params.name == "Praha 7"

    def test_domazlice_resolves_to_production_proven_params(self):
        params = resolve("domazlice")
        assert params.sreality_district_id == 8
        assert params.sreality_region_id == 2
        assert params.remax_regions == {43: (3401,)}
        assert params.bezrealitky_region_id == "R441864"

    @pytest.mark.parametrize("spelling", ["Praha 7", "praha-7", "PRAHA 7", "praha 7"])
    def test_free_text_spellings_resolve(self, spelling):
        assert resolve(spelling).slug == "praha-7"

    def test_okres_prefix_resolves(self):
        assert resolve("okres Domažlice").slug == "domazlice"

    def test_diacritics_are_optional(self):
        assert resolve("Ústí nad Labem").slug == "usti-nad-labem"
        assert resolve("usti nad labem").slug == "usti-nad-labem"


class TestResolveRegions:
    """A kraj resolves to a region-level search: no sreality district id,
    every remax district of the kraj, the kraj's bezrealitky id."""

    def test_plzensky_kraj_resolves_region_wide(self):
        params = resolve("plzensky")
        assert params.sreality_district_id is None
        assert params.sreality_region_id == 2
        (region_id, district_ids), = params.remax_regions.items()
        assert region_id == 43
        assert len(district_ids) == 7
        assert 3401 in district_ids
        assert params.bezrealitky_region_id.startswith("R")

    def test_praha_region_uses_the_frontend_verified_id(self):
        params = resolve("praha")
        assert params.sreality_district_id is None
        assert params.sreality_region_id == 10
        assert params.bezrealitky_region_id == "R435541"
        assert len(params.remax_regions[19]) == 10


class TestResolveFailure:
    """An unknown place fails loudly with nearest-match suggestions."""

    def test_typo_suggests_the_intended_place(self):
        with pytest.raises(PlaceNotFoundError) as excinfo:
            resolve("domzlice")
        assert "domazlice" in excinfo.value.suggestions
        assert "domazlice" in str(excinfo.value)

    def test_nonsense_raises_without_suggestions(self):
        with pytest.raises(PlaceNotFoundError) as excinfo:
            resolve("xyzzy quux")
        assert excinfo.value.suggestions == ()

    def test_every_search_place_resolves_by_its_name(self):
        """Each kraj, okres and obvod in the gazetteer is a search place."""
        from rentczecher_engine.adapters.geocoding.gazetteer import open_gazetteer
        conn = open_gazetteer()
        stmt = "SELECT name FROM kraje UNION ALL SELECT name FROM okresy UNION ALL SELECT name FROM obvody"
        names = [row["name"] for row in conn.execute(stmt)]
        conn.close()
        assert len(names) == 100
        for name in names:
            assert resolve(name).name == name


class TestPlaceParamsImmutability:
    def test_fields_cannot_be_reassigned(self):
        params = resolve("praha-7")
        with pytest.raises(dataclasses.FrozenInstanceError):
            params.slug = "other"  # type: ignore[misc]

    def test_params_type_is_shared(self):
        assert isinstance(resolve("praha-7"), PlaceParams)
