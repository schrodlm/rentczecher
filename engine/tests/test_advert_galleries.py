"""Tests for reading a listing's whole gallery from its advert page.

Run: python3 -m pytest tests/test_advert_galleries.py -v
"""

import httpx
import pytest

from rentczecher_engine.adapters.photos.advert_galleries import HttpAdvertGalleryReader
from rentczecher_engine.adapters.scrapers.client import build_client
from rentczecher_engine.domain.errors import PhotoRefusedError, ScraperBrokenError

REMAX_PAGE = ('<div class="gallery"><a data-fancybox="images" href="https://mlsf.remax-czech.cz/data/1/a.png">'
              '</a></div>')


def _reader(handler):
    return HttpAdvertGalleryReader(build_client(transport=httpx.MockTransport(handler)))


class TestHttpAdvertGalleryReader:
    def test_reads_the_gallery_with_the_portals_parser(self):
        reader = _reader(lambda request: httpx.Response(200, text=REMAX_PAGE))
        assert reader.read("remax", "https://www.remax-czech.cz/reality/detail/1") == (
            "https://mlsf.remax-czech.cz/data/1/a.png",)

    def test_a_portal_without_a_parser_is_broken(self):
        reader = _reader(lambda request: httpx.Response(200, text=REMAX_PAGE))
        with pytest.raises(ScraperBrokenError):
            reader.read("sreality", "https://www.sreality.cz/detail/1")

    def test_a_refusal_reaches_the_caller(self):
        reader = _reader(lambda request: httpx.Response(429))
        with pytest.raises(PhotoRefusedError):
            reader.read("remax", "https://www.remax-czech.cz/reality/detail/1")
