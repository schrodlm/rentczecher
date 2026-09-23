from collections.abc import Callable, Iterable
from typing import cast

import httpx

from rentczecher.adapters.scrapers.base import BaseScraper
from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher.adapters.scrapers.remax import RemaxScraper
from rentczecher.adapters.scrapers.sreality import SrealityScraper
from rentczecher.domain.search import SearchSpec
from rentczecher.services.scrape import Scraper

ALL_SCRAPERS: dict[str, Callable[[SearchSpec, httpx.Client], BaseScraper]] = {
    "sreality": SrealityScraper,
    "bezrealitky": BezrealitkyScraper,
    "remax": RemaxScraper,
}


def scraper_registry(names: Iterable[str] | None = None) -> dict[str, Callable[[SearchSpec, object], Scraper]]:
    """ALL_SCRAPERS narrowed to the given names (or every scraper). Code
    behind the services boundary types the HTTP client as a bare object
    (it cannot import httpx), so each concrete scraper constructor is
    widened here at the adapter edge."""
    selected = ALL_SCRAPERS if names is None else {
        name: cls for name, cls in ALL_SCRAPERS.items() if name in names}
    return {name: cast(Callable[[SearchSpec, object], Scraper], cls) for name, cls in selected.items()}
