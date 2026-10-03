"""Tests for the Location model: which of its units is the most specific.

Run: python3 -m pytest tests/test_domain_location.py -v
"""

from dataclasses import replace

from rentczecher_engine.domain.location import Location, Place

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
)


class TestMostSpecific:
    def test_a_street_outranks_every_area(self):
        street = Place(code=1, name="Škarmanská", lat=49.396, lon=13.04)
        location = replace(ONLY_KRAJ, okres=OKRES, obec=OBEC, obvod=OBVOD, mestska_cast=MESTSKA_CAST,
                           cast_obce=CAST_OBCE, ulice=street)
        assert location.most_specific() == ("ulice", street)

    def test_a_cast_obce_outranks_its_mestska_cast_and_obvod(self):
        location = replace(ONLY_KRAJ, obvod=OBVOD, mestska_cast=MESTSKA_CAST, cast_obce=CAST_OBCE)
        assert location.most_specific() == ("cast_obce", CAST_OBCE)

    def test_a_mestska_cast_outranks_its_obvod(self):
        location = replace(ONLY_KRAJ, obvod=OBVOD, mestska_cast=MESTSKA_CAST)
        assert location.most_specific() == ("mestska_cast", MESTSKA_CAST)

    def test_an_obec_outranks_its_okres(self):
        location = replace(ONLY_KRAJ, okres=OKRES, obec=OBEC)
        assert location.most_specific() == ("obec", OBEC)

    def test_a_kraj_alone_is_the_most_specific(self):
        assert ONLY_KRAJ.most_specific() == ("kraj", KRAJ)
