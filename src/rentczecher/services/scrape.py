"""Run every enabled scraper for a profile, isolating one portal's failure
from the rest."""

import logging
from collections.abc import Callable, Mapping
from typing import Protocol, TypeVar

from rentczecher.domain.errors import PlaceNotFoundError, ScraperBrokenError
from rentczecher.domain.listing import Listing
from rentczecher.domain.search import SearchSpec
from rentczecher.services.pipeline import ScraperHealth

log = logging.getLogger("rentczecher")

ClientT = TypeVar("ClientT")


class Scraper(Protocol):
    def scrape(self) -> list[Listing]:
        ...


def scrape_all(
    scraper_classes: Mapping[str, Callable[[SearchSpec, ClientT], Scraper]],
    spec: SearchSpec,
    client: ClientT,
) -> tuple[list[Listing], dict[str, ScraperHealth]]:
    """Run each scraper in turn, recording its health rather than letting
    one portal's failure hide the others' listings.

    A PlaceNotFoundError is not caught here: it means the profile's place
    could not be resolved for any portal, so the caller aborts the whole
    profile rather than isolating it per scraper.
    """
    listings: list[Listing] = []
    health: dict[str, ScraperHealth] = {}

    for name, scraper_cls in scraper_classes.items():
        log.info("Running scraper: %s", name)
        try:
            scraper = scraper_cls(spec, client)
            found = scraper.scrape()
        except ScraperBrokenError as error:
            log.error("  %s: portal changed its contract - scraper needs updating: %s", name, error)
            health[name] = ScraperHealth(status="broken", error=str(error), listing_count=0)
            continue
        except PlaceNotFoundError:
            raise
        except Exception:
            log.exception("  %s: scraper failed", name)
            health[name] = ScraperHealth(status="broken", error=None, listing_count=0)
            continue

        if len(found) == 0:
            log.warning("  %s: returned 0 results - site structure may have changed!", name)
            health[name] = ScraperHealth(status="zero_results", error=None, listing_count=0)
        else:
            log.info("  %s: found %d listings", name, len(found))
            health[name] = ScraperHealth(status="ok", error=None, listing_count=len(found))
        listings.extend(found)

    return listings, health
