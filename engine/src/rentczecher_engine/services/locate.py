"""Where is this listing? Its location text, resolved against the gazetteer."""

from typing import Protocol

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import Location, ParsedPlace, PlaceRef


class PlaceResolver(Protocol):
    def resolve(self, place: ParsedPlace, within: PlaceRef | None = None) -> Location | None:
        ...


def locate(listing: Listing, gazetteer: PlaceResolver, searched_in: PlaceRef | None) -> Location | None:
    """Where the listing's text says it lies, or None when the text cannot
    be resolved. The place it was searched in, when there was one, only
    breaks a tie the text leaves. A GPS point never stands in: it would claim a place the portal
    did not name."""
    return gazetteer.resolve(listing.parsed_place, within=searched_in)


def locate_listings(
    listings: list[Listing], gazetteer: PlaceResolver, searched_in: PlaceRef | None,
) -> list[Listing]:
    return [
        listing.with_annotations(resolved_location=locate(listing, gazetteer, searched_in)) for listing in listings
    ]
