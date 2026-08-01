"""Tests for the place resolver over the shipped location table.

Run: python3 -m pytest tests/test_location_resolver.py -v
"""

import dataclasses

import pytest

from rentczecher.adapters.scrapers.location_resolver import (
    PlaceNotFoundError,
    PlaceParams,
    normalize_name,
    resolve,
    slugify,
)


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

    def test_every_shipped_slug_resolves_to_itself(self):
        import json
        from rentczecher.adapters.scrapers.location_resolver import PLACES_PATH
        places = json.loads(PLACES_PATH.read_text())
        for row in places["regions"] + places["districts"]:
            assert resolve(row["slug"]).slug == row["slug"]


class TestPlaceParamsImmutability:
    def test_fields_cannot_be_reassigned(self):
        params = resolve("praha-7")
        with pytest.raises(dataclasses.FrozenInstanceError):
            params.slug = "other"  # type: ignore[misc]

    def test_params_type_is_shared(self):
        assert isinstance(resolve("praha-7"), PlaceParams)
