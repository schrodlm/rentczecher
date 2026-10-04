"""Tests for the Location model: which of its units is the most specific,
and which places it lies in.

Run: python3 -m pytest tests/test_domain_location.py -v
"""

from dataclasses import replace

from rentczecher_engine.domain.location import Location, Place, PlaceRef

KRAJ = Place(code=43, name="Plzeňský kraj", lat=49.7, lon=13.4)
OKRES = Place(code=3401, name="Domažlice", lat=49.4, lon=12.9)
OBEC = Place(code=553786, name="Kdyně", lat=49.39, lon=13.04)
OBVOD = Place(code=78, name="Praha 7", lat=50.10, lon=14.44)
MESTSKA_CAST = Place(code=500186, name="Praha 7", lat=50.10, lon=14.43)
CAST_OBCE = Place(code=490067, name="Holešovice", lat=50.10, lon=14.44)
ONLY_KRAJ = Location(
    kraj=KRAJ,
    okres=None,
    obec=None,
    obvod=None,
    mestska_cast=None,
    cast_obce=None,
    ulice=None,
    cislo_popisne=None,
    cislo_orientacni=None,
)
IN_HOLESOVICE = replace(ONLY_KRAJ, obvod=OBVOD, mestska_cast=MESTSKA_CAST, cast_obce=CAST_OBCE)


class TestMostSpecific:
    def test_a_street_outranks_every_area(self):
        street = Place(code=1, name="Škarmanská", lat=49.396, lon=13.04)
        location = replace(ONLY_KRAJ, okres=OKRES, obec=OBEC, obvod=OBVOD, mestska_cast=MESTSKA_CAST,
                           cast_obce=CAST_OBCE, ulice=street)
        assert location.most_specific() == ("ulice", street)

    def test_a_cast_obce_outranks_its_mestska_cast_and_obvod(self):
        assert IN_HOLESOVICE.most_specific() == ("cast_obce", CAST_OBCE)

    def test_a_mestska_cast_outranks_its_obvod(self):
        location = replace(ONLY_KRAJ, obvod=OBVOD, mestska_cast=MESTSKA_CAST)
        assert location.most_specific() == ("mestska_cast", MESTSKA_CAST)

    def test_an_obec_outranks_its_okres(self):
        location = replace(ONLY_KRAJ, okres=OKRES, obec=OBEC)
        assert location.most_specific() == ("obec", OBEC)

    def test_a_kraj_alone_is_the_most_specific(self):
        assert ONLY_KRAJ.most_specific() == ("kraj", KRAJ)


class TestLiesIn:
    def test_a_location_lies_in_each_unit_it_holds(self):
        assert IN_HOLESOVICE.lies_in(PlaceRef("kraj", 43))
        assert IN_HOLESOVICE.lies_in(PlaceRef("obvod", 78))
        assert IN_HOLESOVICE.lies_in(PlaceRef("mestska_cast", 500186))
        assert IN_HOLESOVICE.lies_in(PlaceRef("cast_obce", 490067))

    def test_a_code_matches_only_within_its_kind(self):
        """Codes repeat across kinds: obvod 78 is not cast_obce 78."""
        assert not IN_HOLESOVICE.lies_in(PlaceRef("cast_obce", 78))

    def test_a_location_does_not_lie_in_another_unit_of_a_kind_it_holds(self):
        assert not IN_HOLESOVICE.lies_in(PlaceRef("obvod", 19))

    def test_a_kind_left_open_matches_no_place(self):
        assert not IN_HOLESOVICE.lies_in(PlaceRef("ulice", 467103))
