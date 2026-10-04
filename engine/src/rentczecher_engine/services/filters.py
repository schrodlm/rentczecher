"""Filter scraped listings against a search's own constraints - the ones a
portal's own search params can't be trusted to enforce."""

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.search import SearchSpec


def apply_filters(listings: list[Listing], spec: SearchSpec) -> list[Listing]:
    result = listings
    if spec.dispositions:
        disp_lower = {d.lower() for d in spec.dispositions}
        result = [
            l for l in result
            if l.disposition_raw_text is None or l.disposition_raw_text.lower() in disp_lower
        ]

    if spec.min_size_m2 > 0:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= spec.min_size_m2]

    if spec.min_land_m2 > 0:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= spec.min_land_m2]

    return result
