"""Classify a run's surviving listings against what was seen before.

Pure: every input is already resolved by the caller, including which
listings are disappeared. classify only sorts today's survivors into new
and price-dropped, and annotates the latter with their old price.
"""

from dataclasses import dataclass

from rentczecher.domain.listing import DisappearedListing, Listing


@dataclass(frozen=True, slots=True)
class DiffResult:
    new: list[Listing]
    price_drops: list[Listing]
    disappeared: list[DisappearedListing]


def classify(
    listings: list[Listing],
    seen_ids: set[str],
    latest_prices: dict[str, int],
    disappeared: list[DisappearedListing],
) -> DiffResult:
    new = [listing for listing in listings if listing.id not in seen_ids]
    new_ids = {listing.id for listing in new}

    price_drops = []
    for listing in listings:
        if listing.id in new_ids:
            continue
        old_price = latest_prices.get(listing.id)
        if old_price and listing.price and old_price > listing.price:
            price_drops.append(listing.with_annotations(price_drop_from=old_price))

    return DiffResult(new=new, price_drops=price_drops, disappeared=disappeared)
