"""Reads RÚIAN's address-point dump (OB_ADR): one CSV per obec, one row per
address. It supplies what the state file lacks, the streets, and the
overlaps, since every address names exactly one unit of each kind."""

import csv
import io
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pyproj import Transformer

from ..model import Overlaps, Position, Ulice

# Columns of the address CSV (semicolon-separated, cp1250).
_OBEC_CODE = 1
_MESTSKA_CAST_CODE = 3
_CAST_OBCE_CODE = 7
_ULICE_CODE = 9
_ULICE_NAME = 10
_COORD_Y = 16
_COORD_X = 17


@dataclass
class _StreetPoints:
    """The address points of one street seen so far."""

    name: str
    obec_code: int
    sum_y: float = 0.0
    sum_x: float = 0.0
    count: int = 0


@dataclass
class _Pairs:
    casti_obce_mestske_casti: set[tuple[int, int]] = field(default_factory=set)
    ulice_mestske_casti: set[tuple[int, int]] = field(default_factory=set)
    ulice_casti_obce: set[tuple[int, int]] = field(default_factory=set)


class RuianAddressDump:
    """The streets and overlaps of one OB_ADR dump, read once."""

    def __init__(self, path: Path):
        # The CSV publishes S-JTSK Y and X as positive numbers. EPSG:5514 is
        # negative-signed, hence the sign flips.
        self._to_wgs84 = Transformer.from_crs("EPSG:5514", "EPSG:4326", always_xy=True)
        self._streets: dict[int, _StreetPoints] = {}
        self._pairs = _Pairs()
        for row in _rows(path):
            self._read(row)

    def ulice(self) -> list[Ulice]:
        """Every street with at least one located address, at the mean
        position of its addresses."""
        streets = []
        for code, points in self._streets.items():
            if points.count == 0:
                continue
            lon, lat = self._to_wgs84.transform(-points.sum_y / points.count, -points.sum_x / points.count)
            streets.append(Ulice(code=code, name=points.name, obec_code=points.obec_code,
                                 position=Position(lat=round(lat, 6), lon=round(lon, 6))))
        return streets

    def overlaps(self) -> Overlaps:
        """The overlap pairs. A street without a located address is not
        stored, so its pairs are left out too."""
        located = {code for code, points in self._streets.items() if points.count > 0}
        return Overlaps(
            casti_obce_mestske_casti=frozenset(self._pairs.casti_obce_mestske_casti),
            ulice_mestske_casti=frozenset(
                pair for pair in self._pairs.ulice_mestske_casti if pair[0] in located),
            ulice_casti_obce=frozenset(
                pair for pair in self._pairs.ulice_casti_obce if pair[0] in located),
        )

    def _read(self, row: list[str]) -> None:
        cast_obce = int(row[_CAST_OBCE_CODE])
        mestska_cast = int(row[_MESTSKA_CAST_CODE]) if row[_MESTSKA_CAST_CODE] else None
        ulice = int(row[_ULICE_CODE]) if row[_ULICE_CODE] else None

        if mestska_cast is not None:
            self._pairs.casti_obce_mestske_casti.add((cast_obce, mestska_cast))
        if ulice is None:
            return
        self._pairs.ulice_casti_obce.add((ulice, cast_obce))
        if mestska_cast is not None:
            self._pairs.ulice_mestske_casti.add((ulice, mestska_cast))

        points = self._streets.setdefault(ulice, _StreetPoints(row[_ULICE_NAME], int(row[_OBEC_CODE])))
        if row[_COORD_Y] and row[_COORD_X]:
            points.sum_y += float(row[_COORD_Y])
            points.sum_x += float(row[_COORD_X])
            points.count += 1


def _rows(path: Path) -> Iterator[list[str]]:
    """Every address row across the dump's per-obec files."""
    with zipfile.ZipFile(path) as bundle:
        for name in bundle.namelist():
            with bundle.open(name) as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="cp1250"), delimiter=";")
                next(reader, None)
                yield from reader
