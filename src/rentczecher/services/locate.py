"""Where is this listing? Portal GPS when given, offline geocoding otherwise."""

from dataclasses import dataclass

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.domain.listing import Listing


@dataclass(frozen=True, slots=True)
class LocatedPoint:
    lat: float
    lon: float
    tier: str  # 'gps' for a portal-provided point, else the resolution tier


def locate(listing: Listing, gazetteer: Gazetteer) -> LocatedPoint | None:
    """Coordinates for a listing, or None when nothing trustworthy exists."""
    if listing.lat is not None and listing.lon is not None:
        return LocatedPoint(lat=listing.lat, lon=listing.lon, tier="gps")
    place = gazetteer.resolve(listing.parsed_place)
    if place is None:
        return None
    return LocatedPoint(lat=place.lat, lon=place.lon, tier=place.tier)
