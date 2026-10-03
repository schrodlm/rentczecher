"""The rows the gazetteer stores, one type per table, as the RÚIAN readers
produce them and the database writes them."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """The mean position of a place's address points."""

    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class Kraj:
    code: int
    name: str
    position: Position


@dataclass(frozen=True, slots=True)
class Okres:
    code: int
    name: str
    kraj_code: int
    position: Position


@dataclass(frozen=True, slots=True)
class Obec:
    code: int
    name: str
    okres_code: int | None
    kraj_code: int
    position: Position


@dataclass(frozen=True, slots=True)
class Obvod:
    code: int
    name: str
    obec_code: int
    position: Position


@dataclass(frozen=True, slots=True)
class MestskaCast:
    code: int
    name: str
    obec_code: int
    obvod_code: int | None
    position: Position


@dataclass(frozen=True, slots=True)
class CastObce:
    code: int
    name: str
    obec_code: int
    position: Position


@dataclass(frozen=True, slots=True)
class Ulice:
    code: int
    name: str
    obec_code: int
    position: Position


@dataclass(frozen=True, slots=True)
class Overlaps:
    """Pairs of places seen together on at least one address point."""

    casti_obce_mestske_casti: frozenset[tuple[int, int]]
    ulice_mestske_casti: frozenset[tuple[int, int]]
    ulice_casti_obce: frozenset[tuple[int, int]]
