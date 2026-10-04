"""Filter scraped listings against a search's own constraints - the ones a
portal's own search params can't be trusted to enforce."""

from rentczecher_engine.domain.disposition import parse_disposition
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.search import SearchSpec


def apply_filters(listings: list[Listing], spec: SearchSpec) -> list[Listing]:
    result = listings
    if spec.dispositions:
        allowed = {parse_disposition(raw) for raw in spec.dispositions}
        result = [l for l in result if l.disposition is None or l.disposition in allowed]

    if spec.min_size_m2 > 0:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= spec.min_size_m2]

    if spec.min_land_m2 > 0:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= spec.min_land_m2]

    return result
