from rentczecher.adapters.scrapers.sreality import SrealityScraper
from rentczecher.adapters.scrapers.bezrealitky import BezrealitkyScraper
from rentczecher.adapters.scrapers.remax import RemaxScraper

ALL_SCRAPERS = {
    "sreality": SrealityScraper,
    "bezrealitky": BezrealitkyScraper,
    "remax": RemaxScraper,
}
