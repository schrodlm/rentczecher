from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedPlace:
    """Place names scraped from one listing, before gazetteer resolution.

    Which kind of place a name is (street, town, part) is discovered by
    gazetteer lookup, so names carry no labels. The district (okres) is the
    one exception lookup cannot discover. A district shares its name with a
    town, so a portal whose format states the district fills it here, and
    that name never doubles as a town.

    House numbers, when the portal gives them, are kept as written.
    """

    names: tuple[str, ...] = ()
    district: str | None = None
    cislo_popisne: str | None = None
    cislo_orientacni: str | None = None


@dataclass(frozen=True, slots=True)
class Place:
    """One RÚIAN unit, at the mean position of its address points. Its code
    is unique only within its kind, which the field holding it states."""

    code: int
    name: str
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class Location:
    """Where something lies: the RÚIAN unit of each kind, kraj to ulice, plus
    the house numbers as written. A kind left open is None, and Praha lies
    in no okres."""

    kraj: Place
    okres: Place | None
    obec: Place | None
    obvod: Place | None
    mestska_cast: Place | None
    cast_obce: Place | None
    ulice: Place | None
    cislo_popisne: str | None
    cislo_orientacni: str | None

    def most_specific(self) -> tuple[str, Place]:
        """The finest unit named, with its kind."""
        if self.ulice is not None:
            return "ulice", self.ulice
        if self.cast_obce is not None:
            return "cast_obce", self.cast_obce
        if self.mestska_cast is not None:
            return "mestska_cast", self.mestska_cast
        if self.obvod is not None:
            return "obvod", self.obvod
        if self.obec is not None:
            return "obec", self.obec
        if self.okres is not None:
            return "okres", self.okres
        return "kraj", self.kraj
