"""Where is this listing? Text resolution first, geometry when text fails."""

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.domain.listing import Listing
from rentczecher.domain.location import ResolvedPlace


def locate(listing: Listing, gazetteer: Gazetteer) -> ResolvedPlace | None:
    """The place a listing belongs to, or None when nothing trustworthy exists.

    Text resolution runs first, when it is ambiguous but the portal gave
    GPS, reverse geocoding steps in instead. None means neither source can
    be trusted - unresolvable text, or GPS outside every Czech municipality
    (noise) alike.
    """
    place = gazetteer.resolve(listing.parsed_place)
    if place is None and listing.lat is not None and listing.lon is not None:
        place = gazetteer.reverse(listing.lat, listing.lon)
    return place


def locate_listings(listings: list[Listing], gazetteer: Gazetteer) -> list[Listing]:
    return [listing.with_annotations(place=locate(listing, gazetteer)) for listing in listings]
