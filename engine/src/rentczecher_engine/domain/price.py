from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceObservation:
    """One append-only price point for a listing."""

    listing_id: str
    price: int
    observed_at: str
    charges: int | None = None
    observed_in_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class PriceChange:
    """A price a listing held, from the first to the last scan that saw it.
    The charges are the ones last seen at that price."""

    price: int
    charges: int | None
    first_seen_at: str
    last_seen_at: str


@dataclass(frozen=True, slots=True)
class PostingPrices:
    """The prices one portal posting of a property held, oldest first."""

    listing_id: str
    source: str
    url: str
    changes: tuple[PriceChange, ...]


def price_changes(observations: list[PriceObservation]) -> list[PriceChange]:
    """Collapses observations, oldest first, into the prices they held. A
    repeat scan at the same price extends that price, whatever its charges."""
    changes: list[PriceChange] = []
    for observation in observations:
        if changes and changes[-1].price == observation.price:
            held = changes[-1]
            changes[-1] = PriceChange(
                price=held.price,
                charges=observation.charges,
                first_seen_at=held.first_seen_at,
                last_seen_at=observation.observed_at,
            )
        else:
            changes.append(PriceChange(
                price=observation.price,
                charges=observation.charges,
                first_seen_at=observation.observed_at,
                last_seen_at=observation.observed_at,
            ))
    return changes
