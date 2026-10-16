"""Filter scraped listings against a search's own constraints - the ones a
portal's own search params can't be trusted to enforce."""

from rentczecher_engine.domain.disposition import Disposition
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria


def apply_filters(listings: list[Listing], criteria: Criteria) -> list[Listing]:
    result = [l for l in listings if _fits_layout(l.disposition, criteria)]

    if criteria.min_size_m2 is not None:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= criteria.min_size_m2]

    if criteria.max_size_m2 is not None:
        result = [l for l in result if l.size_m2 is None or l.size_m2 <= criteria.max_size_m2]

    if criteria.min_land_m2 is not None:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= criteria.min_land_m2]

    return result


def listings_inside(listings: list[Listing], place: PlaceRef) -> list[Listing]:
    """A listing whose location is unknown, or too coarse to tell, is left
    out. Runs on located listings."""
    return [
        listing for listing in listings
        if listing.resolved_location is not None and listing.resolved_location.lies_in(place)
    ]


def _fits_layout(disposition: Disposition | None, criteria: Criteria) -> bool:
    # A listing that states no layout passes: an unknown layout is no mismatch.
    if not criteria.dispositions or disposition is None:
        return True
    return disposition in criteria.dispositions
