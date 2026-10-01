"""Disposition normalization: one layout vocabulary across data sources.

Sources spell the same layout differently (garsoniéra vs 1+kk, 2+KK vs
2+kk), and outside flats the scraped field may hold a building-type label
("Rodinný") rather than a layout. Comparing raw strings across sources
therefore splits real matches.
"""

import re
import unicodedata

# A studio (garsoniéra, garsonka) is a 1+kk by another name.
# TODO: widen with evidence - building-type vocabulary for houses, exotic
# layout categories - once real match data shows which unknown strings matter.
_SYNONYMS = {
    "garsoniera": "1+kk",
    "garsonka": "1+kk",
    "atypicky": "atypicky",
}

_LAYOUT = re.compile(r"^(\d)\s*\+\s*(kk|\d)$")


def normalize_disposition(raw: str | None) -> str | None:
    """Canonical layout ('2+kk', '1+kk', 'atypicky') or None for no evidence.

    Layout strings identify themselves (N+kk, N+N, the studio synonyms);
    anything else - building-type labels, unknown strings - normalizes to
    None, because a wrong mapping is worse than silence.
    """
    if not raw:
        return None
    decomposed = unicodedata.normalize("NFD", raw.casefold().strip())
    flat = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    if flat in _SYNONYMS:
        return _SYNONYMS[flat]
    layout = _LAYOUT.match(flat)
    if layout:
        return f"{layout.group(1)}+{layout.group(2)}"
    return None
