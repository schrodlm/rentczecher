from collections.abc import Callable

from rentczecher.adapters.scrapers.base import BaseScraper
from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher.adapters.scrapers.remax import RemaxScraper
from rentczecher.adapters.scrapers.sreality import SrealityScraper

ALL_SCRAPERS: dict[str, Callable[[dict], BaseScraper]] = {
    "sreality": SrealityScraper,
    "bezrealitky": BezrealitkyScraper,
    "remax": RemaxScraper,
}
