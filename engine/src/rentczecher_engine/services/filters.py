"""Filter scraped listings against a search's own constraints - the ones a
portal's own search params can't be trusted to enforce."""

from rentczecher_engine.domain.disposition import parse_disposition
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.profile import Criteria


def apply_filters(listings: list[Listing], criteria: Criteria) -> list[Listing]:
    result = listings
    if criteria.dispositions:
        allowed = {parse_disposition(raw) for raw in criteria.dispositions}
        result = [l for l in result if l.disposition is None or l.disposition in allowed]

    if criteria.min_size_m2 > 0:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= criteria.min_size_m2]

    if criteria.min_land_m2 > 0:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= criteria.min_land_m2]

    return result
