"""Smart scoring system for ranking listings."""

from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.profile import Preferences


def compute_score(listing: Listing, preferences: Preferences) -> int:
    """Compute a 0-100 smart score for a listing against a profile's preferences."""
    total = 0.0

    # Price per m2 component (for flats/rentals)
    if preferences.price_per_m2_weight and listing.size_m2 and listing.size_m2 > 0:
        price_per_m2 = listing.price / listing.size_m2
        score = max(0.0, min(100.0, (550 - price_per_m2) / 2.5))
        total += score * preferences.price_per_m2_weight / 100

    # Disposition component
    if preferences.disposition_weight and listing.disposition is not None and preferences.preferred_dispositions:
        if listing.disposition in preferences.preferred_dispositions:
            idx = preferences.preferred_dispositions.index(listing.disposition)
            score = max(20.0, 100.0 - idx * 20)
        else:
            score = 10.0
        total += score * preferences.disposition_weight / 100

    # Size component (building/usable area)
    if preferences.size_weight and listing.size_m2 and preferences.ideal_size_m2 > 0:
        score = min(100.0, (listing.size_m2 / preferences.ideal_size_m2) * 100)
        total += score * preferences.size_weight / 100

    # Neighborhood component
    if preferences.neighborhood_weight and listing.location_raw_text and preferences.preferred_neighborhoods:
        loc_lower = listing.location_raw_text.lower()
        score = 20.0
        for i, hood in enumerate(preferences.preferred_neighborhoods):
            if hood.lower() in loc_lower:
                score = max(20.0, 100.0 - i * 20)
                break
        total += score * preferences.neighborhood_weight / 100

    # Land area component (for houses/cottages)
    if preferences.land_weight and listing.land_m2 and preferences.ideal_land_m2 > 0:
        score = min(100.0, (listing.land_m2 / preferences.ideal_land_m2) * 100)
        total += score * preferences.land_weight / 100

    # Total price component (for sale listings - lower price = better)
    if preferences.price_weight and listing.price and preferences.max_good_price > 0:
        # At max_good_price or below = 100, at 2x max_good_price = 0
        ratio = listing.price / preferences.max_good_price
        score = max(0.0, min(100.0, (2.0 - ratio) * 100))
        total += score * preferences.price_weight / 100

    return round(total)
