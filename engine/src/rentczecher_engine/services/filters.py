"""Filter scraped listings against a search's own constraints - the ones a
portal's own search params can't be trusted to enforce."""

from rentczecher_engine.domain.disposition import Disposition
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.profile import Criteria


def apply_filters(listings: list[Listing], criteria: Criteria) -> list[Listing]:
    result = [l for l in listings if _fits_layout(l.disposition, criteria)]

    if criteria.min_size_m2 > 0:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= criteria.min_size_m2]

    if criteria.min_land_m2 > 0:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= criteria.min_land_m2]

    return result


def _fits_layout(disposition: Disposition | None, criteria: Criteria) -> bool:
    # An unknown or atypical layout states no rooms or kitchen, so no bound can fail it.
    if disposition is None or disposition.rooms is None:
        return True
    if criteria.min_rooms is not None and disposition.rooms < criteria.min_rooms:
        return False
    if criteria.max_rooms is not None and disposition.rooms > criteria.max_rooms:
        return False
    return criteria.kitchen is None or disposition.kitchen == criteria.kitchen
