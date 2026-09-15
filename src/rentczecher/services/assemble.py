"""Build a property's canonical identity from one of its listings."""

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.property import PropertyIdentity


def assemble_property(listing: Listing, property_id: str, created_at: str) -> PropertyIdentity:
    """The property row a located listing seeds.

    lat/lon come from the listing's own GPS when present, else its
    resolved place's centroid, else neither is set.
    """
    if listing.lat is not None and listing.lon is not None:
        lat, lon = listing.lat, listing.lon
    elif listing.place is not None:
        lat, lon = listing.place.lat, listing.place.lon
    else:
        lat, lon = None, None

    return PropertyIdentity(
        id=property_id,
        created_at=created_at,
        title=listing.title,
        location=listing.location,
        size_m2=listing.size_m2,
        disposition=listing.disposition,
        land_m2=listing.land_m2,
        lat=lat,
        lon=lon,
    )
