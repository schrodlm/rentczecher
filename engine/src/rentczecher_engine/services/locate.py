"""Where is this listing? Its location text, resolved against the gazetteer."""

from typing import Protocol

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import ParsedPlace, ResolvedPlace


class PlaceResolver(Protocol):
    def resolve(self, place: ParsedPlace) -> ResolvedPlace | None:
        ...


def locate(listing: Listing, gazetteer: PlaceResolver) -> ResolvedPlace | None:
    """The place the listing's text names, or None when the text cannot be
    resolved to one place. A GPS point never stands in: it would claim a
    place the portal did not name."""
    return gazetteer.resolve(listing.parsed_place)


def locate_listings(listings: list[Listing], gazetteer: PlaceResolver) -> list[Listing]:
    return [listing.with_annotations(place=locate(listing, gazetteer)) for listing in listings]
