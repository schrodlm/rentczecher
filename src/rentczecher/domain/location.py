from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedPlace:
    """Place names scraped from one listing, before gazetteer resolution.

    Which kind of place a name is (street, town, part) is discovered by
    gazetteer lookup, so names carry no labels. The district (okres) is the
    one exception lookup cannot discover - a district shares its name with
    a town - so a portal whose format states the district fills it here,
    and that name never doubles as a town.
    """

    names: tuple[str, ...] = ()
    district: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedPlace:
    """A gazetteer's answer to a ParsedPlace: exactly one place, or a
    caller would have gotten None instead."""

    name: str
    muni_name: str | None  # a resolved district has no municipality
    okres_name: str | None
    tier: str
    lat: float
    lon: float
