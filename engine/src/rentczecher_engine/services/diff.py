"""Classify a run's surviving listings against what was seen before.

Pure: every input is already resolved by the caller. classify sorts
today's survivors into new flats and price-dropped postings, annotates
the latter with their old price, and picks out the viewed flats the run
changed.
"""

from dataclasses import dataclass

from rentczecher_engine.domain.dedup import DedupOutcome
from rentczecher_engine.domain.listing import Listing


@dataclass(frozen=True, slots=True)
class DiffResult:
    new: list[Listing]
    price_drops: list[Listing]
    # The keeper of each viewed flat that a portal newly posts or that a
    # posting's price changed on.
    updated_keeper_ids: set[str]


def classify(
    outcome: DedupOutcome,
    located_by_id: dict[str, Listing],
    seen_ids: set[str],
    viewed_ids: set[str],
    latest_prices: dict[str, int],
) -> DiffResult:
    listings = outcome.survivors
    members_by_keeper = outcome.members_by_keeper(located_by_id)
    # A portal newly posting a flat the profile already knows does not make
    # the flat new.
    new = [
        listing for listing in listings
        if not any(member.id in seen_ids or member.id in viewed_ids
                   for member in members_by_keeper[listing.id])
    ]
    new_ids = {listing.id for listing in new}

    price_drops = []
    for listing in listings:
        if listing.id in new_ids:
            continue
        old_price = latest_prices.get(listing.id)
        if old_price and listing.price and old_price > listing.price:
            price_drops.append(listing.with_annotations(price_drop_from=old_price))

    updated_keeper_ids = {
        keeper_id for keeper_id, members in members_by_keeper.items()
        if any(member.id in viewed_ids for member in members)
        and any(_changed(member, seen_ids, latest_prices) for member in members)
    }

    return DiffResult(new=new, price_drops=price_drops, updated_keeper_ids=updated_keeper_ids)


def _changed(listing: Listing, seen_ids: set[str], latest_prices: dict[str, int]) -> bool:
    if listing.id not in seen_ids:
        return True
    old_price = latest_prices.get(listing.id)
    return bool(old_price and listing.price and old_price != listing.price)
