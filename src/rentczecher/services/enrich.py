"""Whether a run enriches its listings with a portal-neutral extra fact -
the decision lives here, the fact itself comes from an injected adapter."""

from collections.abc import Callable

from rentczecher.domain.listing import Listing


def apply_tram_enrichment(
    listings: list[Listing], enabled: bool, enrich: Callable[[Listing], Listing]
) -> list[Listing]:
    if not enabled:
        return listings
    return [enrich(listing) for listing in listings]
