from collections.abc import Callable, Iterable
from typing import cast

import httpx

from rentczecher_engine.adapters.scrapers.base import BaseScraper
from rentczecher_engine.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher_engine.adapters.scrapers.remax import RemaxScraper
from rentczecher_engine.adapters.scrapers.sreality import SrealityScraper
from rentczecher_engine.domain.profile import Criteria, Portal
from rentczecher_engine.services.scrape import Scraper

ALL_SCRAPERS: dict[Portal, Callable[[Criteria, httpx.Client], BaseScraper]] = {
    "sreality": SrealityScraper,
    "bezrealitky": BezrealitkyScraper,
    "remax": RemaxScraper,
}


def scraper_registry(names: Iterable[Portal] | None = None) -> dict[str, Callable[[Criteria, object], Scraper]]:
    """ALL_SCRAPERS narrowed to the given names (or every scraper). Code
    behind the services boundary types the HTTP client as a bare object
    (it cannot import httpx), so each concrete scraper constructor is
    widened here at the adapter edge."""
    selected = ALL_SCRAPERS if names is None else {
        name: cls for name, cls in ALL_SCRAPERS.items() if name in names}
    return {name: cast(Callable[[Criteria, object], Scraper], cls) for name, cls in selected.items()}
