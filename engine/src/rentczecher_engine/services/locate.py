"""Where is this listing? Its location text, resolved against the gazetteer."""

from typing import Protocol

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import Location, ParsedPlace


class PlaceResolver(Protocol):
    def resolve(self, place: ParsedPlace) -> Location | None:
        ...


def locate(listing: Listing, gazetteer: PlaceResolver) -> Location | None:
    """Where the listing's text says it lies, or None when the text cannot
    be resolved. A GPS point never stands in: it would claim a place the
    portal did not name."""
    return gazetteer.resolve(listing.parsed_place)


def locate_listings(listings: list[Listing], gazetteer: PlaceResolver) -> list[Listing]:
    return [listing.with_annotations(resolved_location=locate(listing, gazetteer)) for listing in listings]
