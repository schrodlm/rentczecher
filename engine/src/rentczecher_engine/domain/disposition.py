"""Disposition: a property's layout, one vocabulary across data sources.

Sources spell the same layout differently (garsoniéra vs 1+kk, 2+KK vs
2+kk), and outside flats the scraped field may hold a building-type label
("Rodinný") rather than a layout. Comparing raw strings across sources
therefore splits real matches.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, cast

Kitchen = Literal["kitchenette", "separate"]
DispositionCode = Literal[
    "1+kk", "1+1", "2+kk", "2+1", "3+kk", "3+1", "4+kk", "4+1", "5+kk", "5+1",
    "6+kk", "6+1", "7+kk", "7+1", "8+kk", "8+1", "9+kk", "9+1", "atypicky",
]

# A studio (garsoniéra, garsonka) is a 1+kk by another name.
_STUDIO_SYNONYMS = {"garsoniera", "garsonka"}
_ATYPICAL_CODE: DispositionCode = "atypicky"
_LAYOUT = re.compile(r"^([1-9])\s*\+\s*(kk|1)$")


@dataclass(frozen=True, slots=True)
class Disposition:
    """A layout: its number of rooms and whether the kitchen is a kitchenette
    (2+kk) or a separate room (2+1). An atypical layout has neither."""

    rooms: int | None
    kitchen: Kitchen | None

    def __post_init__(self) -> None:
        if (self.rooms is None) != (self.kitchen is None):
            raise ValueError("a disposition has both rooms and a kitchen, or neither")
        if self.rooms is not None and not 1 <= self.rooms <= 9:
            raise ValueError("a disposition has 1 to 9 rooms")

    @property
    def code(self) -> DispositionCode:
        """The canonical spelling: '2+kk', '2+1' or 'atypicky'."""
        if self.rooms is None or self.kitchen is None:
            return _ATYPICAL_CODE
        return cast(DispositionCode, f"{self.rooms}+{'kk' if self.kitchen == 'kitchenette' else '1'}")


ATYPICAL = Disposition(rooms=None, kitchen=None)


def parse_disposition(raw: str | None) -> Disposition | None:
    """The layout a scraped string names, or None when it names none.

    Layout strings identify themselves (N+kk, N+1, the studio synonyms,
    atypický). Anything else, a building-type label or an unknown string,
    is None, because a wrong layout is worse than no layout.
    """
    if not raw:
        return None
    decomposed = unicodedata.normalize("NFD", raw.casefold().strip())
    flat = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    if flat in _STUDIO_SYNONYMS:
        return Disposition(rooms=1, kitchen="kitchenette")
    if flat == _ATYPICAL_CODE:
        return ATYPICAL
    layout = _LAYOUT.match(flat)
    if layout is None:
        return None
    kitchen: Kitchen = "kitchenette" if layout.group(2) == "kk" else "separate"
    return Disposition(rooms=int(layout.group(1)), kitchen=kitchen)
