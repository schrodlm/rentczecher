"""Build a property's stored identity and location from its listings."""

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import Location
from rentczecher_engine.domain.property import PropertyIdentity, PropertyLocation


def assemble_property(listing: Listing, property_id: str, created_at: str) -> PropertyIdentity:
    """The property row a located listing seeds.

    lat/lon come from the listing's own GPS when present, else its most
    specific resolved unit's position, else neither is set.
    """
    if listing.lat is not None and listing.lon is not None:
        lat, lon = listing.lat, listing.lon
    elif listing.resolved_location is not None:
        _, place = listing.resolved_location.most_specific()
        lat, lon = place.lat, place.lon
    else:
        lat, lon = None, None

    return PropertyIdentity(
        id=property_id,
        created_at=created_at,
        title=listing.title,
        location_raw_text=listing.location_raw_text,
        size_m2=listing.size_m2,
        disposition_raw_text=listing.disposition_raw_text,
        land_m2=listing.land_m2,
        lat=lat,
        lon=lon,
    )


def assemble_location(location: Location) -> PropertyLocation:
    """The stored form of a resolved location: each unit by its code."""
    return PropertyLocation(
        kraj_code=location.kraj.code,
        okres_code=location.okres.code if location.okres is not None else None,
        obec_code=location.obec.code if location.obec is not None else None,
        obvod_code=location.obvod.code if location.obvod is not None else None,
        mestska_cast_code=location.mestska_cast.code if location.mestska_cast is not None else None,
        cast_obce_code=location.cast_obce.code if location.cast_obce is not None else None,
        ulice_code=location.ulice.code if location.ulice is not None else None,
        cislo_popisne=location.cislo_popisne,
        cislo_orientacni=location.cislo_orientacni,
    )
