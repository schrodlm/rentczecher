from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceObservation:
    """One append-only price point for a listing."""

    listing_id: str
    price: int
    observed_at: str
    charges: int | None = None
    observed_in_run_id: str | None = None
