import httpx

from rentczecher_engine.adapters.photos.fetcher import HttpAdvertPageFetcher
from rentczecher_engine.adapters.scrapers import ADVERT_GALLERY_PARSERS
from rentczecher_engine.domain.errors import ScraperBrokenError


class HttpAdvertGalleryReader:
    """Reads a listing's whole gallery from its advert page, with the parser
    of the listing's portal."""

    def __init__(self, client: httpx.Client):
        self._pages = HttpAdvertPageFetcher(client)

    def read(self, source: str, url: str) -> tuple[str, ...]:
        """Raises what fetching the page raises, and ScraperBrokenError for a
        page the portal's parser cannot read."""
        parse = ADVERT_GALLERY_PARSERS.get(source)
        if parse is None:
            raise ScraperBrokenError(f"{source}: no parser reads its advert pages")
        return parse(self._pages.fetch(url))
