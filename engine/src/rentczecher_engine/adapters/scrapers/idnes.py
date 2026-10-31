import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import unquote, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from rentczecher_engine.adapters.scrapers.base import BaseScraper, Listing
from rentczecher_engine.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher_engine.adapters.scrapers.parsing import parse_comma_separated_address
from rentczecher_engine.domain.errors import ScraperBrokenError
from rentczecher_engine.domain.location import PlaceKind

log = logging.getLogger("rentczecher")

SITE_URL = "https://reality.idnes.cz"
SEARCH_URL = f"{SITE_URL}/s/"
# Hard bound on one search's pages, so no pagination quirk can keep a scan
# reading the portal.
MAX_PAGES = 50

OFFER_VALUE = {"rent": "lease", "sale": "sale"}
# The portal files cottages as a house subtype, which a house search leaves
# out.
ESTATE_TYPE_QUERY: dict[str, tuple[tuple[str, str], ...]] = {
    "flat": (("f[type]", "flat"),),
    "house": (("f[type]", "house"), ("f[subtypeHouse][]", "house")),
    "cottage": (("f[type]", "house"), ("f[subtypeHouse][]", "cabin")),
    "land": (("f[type]", "land"),),
}
# The portal names its localities by RÚIAN unit type and code.
LOCALITY_PREFIX: dict[PlaceKind, str] = {"kraj": "VUSC", "okres": "OKRES", "obvod": "MOP"}

DETAIL_PATH = re.compile(r"/detail/[^?#]+/([0-9a-f]{24})/?$")
# A title groups digits and joins the unit with a no-break space
# ("domu 352\xa0m² s pozemkem 1\xa0255\xa0m²"), while a plain space follows
# the disposition ("bytu 3+1 120\xa0m²"), so only a no-break space groups.
AREA_RE = re.compile(r"(\d{1,3}(?:\xa0\d{3})*)\xa0?m²")
LAND_RE = re.compile(r"s pozemkem (\d{1,3}(?:\xa0\d{3})*)\xa0?m²")
DISPOSITION_RE = re.compile(r"\b(\d\+(?:kk|\d))")


def gallery_from_advert_page(html: str) -> tuple[str, ...]:
    """The full-size photos the advert page's gallery links to, in its order."""
    gallery = BeautifulSoup(html, "lxml").select_one("div.b-gallery")
    if gallery is None:
        raise ScraperBrokenError("idnes: advert page carries no gallery")
    urls = []
    # The gallery's videos and 3D tours open from the same carousel, marked
    # by attributes of their own.
    photo_links = gallery.select(
        'a[data-fancybox="images"]:not([data-fancybox-video]):not([data-fancybox-virtual]):not([data-type])')
    for link in photo_links:
        href = str(link.get("href", ""))
        if href:
            urls.append(urljoin(SITE_URL, href))
    return tuple(dict.fromkeys(urls))


@dataclass(frozen=True, slots=True)
class IdnesPlace:
    locality: str

    @classmethod
    def from_params(cls, place: PlaceParams) -> "IdnesPlace":
        area = place.search_area
        return cls(locality=f"{LOCALITY_PREFIX[area.kind]}-{area.code}")


@dataclass(frozen=True, slots=True)
class SearchPage:
    listings: list[Listing]
    # Every result card with a detail link, before filtering.
    card_ids: set[str]
    next_url: str | None


def _is_allowed_search_url(url: str) -> bool:
    """Whether a search URL stays inside what robots.txt allows: no price
    floor, no multi-value filter and no sorting."""
    parts = urlsplit(url)
    query = unquote(parts.query)
    return (parts.netloc == "reality.idnes.cz" and parts.path.startswith("/s/")
            and "cena-nad-" not in parts.path and "|" not in query and "sort" not in query)


def _square_metres(match: re.Match[str] | None) -> int | None:
    return int(match.group(1).replace("\xa0", "")) if match else None


def _price_of(text: str) -> int | None:
    """The whole price a card states, monthly for a rental, or None when it
    states none ('Cena na vyžádání') or prices by another unit."""
    amount, currency, unit = text.partition("Kč")
    digits = re.sub(r"\D", "", amount)
    if not currency or not digits or unit.strip() not in ("", "/měsíc"):
        return None
    return int(digits)


class IdnesScraper(BaseScraper):
    name = "idnes"

    def __init__(self, criteria, client):
        super().__init__(criteria, client)
        self.place = IdnesPlace.from_params(resolve(criteria.place))

    def _build_url(self) -> str:
        query: list[tuple[str, object]] = [("f[offer]", OFFER_VALUE[self.criteria.offer_type])]
        query += ESTATE_TYPE_QUERY[self.criteria.estate_type]
        query.append(("f[locality]", self.place.locality))
        if self.criteria.max_price is not None:
            query.append(("f[priceMax]", self.criteria.max_price))
        # robots.txt disallows the URL a price floor redirects to, so
        # min_price filters the cards only.
        return SEARCH_URL + "?" + urlencode(query)

    def scrape(self) -> list[Listing]:
        """Requests only the search form and the next-page links the portal
        serves. Raises ScraperBrokenError for a next-page link robots.txt
        rules out."""
        listings: dict[str, Listing] = {}
        seen_card_ids: set[str] = set()
        url = self._build_url()
        for _ in range(MAX_PAGES):
            page = self._parse_page(self._fetch(url))
            for listing in page.listings:
                listings.setdefault(listing.id, listing)
            # A page of cards already read means the portal is serving the
            # same page again, not that the search goes on.
            repeated = page.card_ids <= seen_card_ids
            seen_card_ids |= page.card_ids
            if not page.card_ids or page.next_url is None or repeated:
                break
            if not _is_allowed_search_url(page.next_url):
                raise ScraperBrokenError(f"idnes: next page {page.next_url} is a URL robots.txt rules out")
            url = page.next_url
            time.sleep(1.5)
        else:
            log.warning("idnes: pagination cap of %d pages reached - results may be incomplete", MAX_PAGES)
        return list(listings.values())

    def _fetch(self, url: str) -> str:
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_page(self, html: str) -> SearchPage:
        """A search without results lists other adverts as similar offers,
        outside the results, so only the results' cards are read."""
        soup = BeautifulSoup(html, "lxml")
        listings = []
        card_ids: set[str] = set()
        for card in soup.select("div.c-products__item"):
            link = card.select_one("a.c-products__link")
            href = str(link.get("href", "")) if link is not None else ""
            match = DETAIL_PATH.search(href)
            if match is None:
                continue
            listing_id = match.group(1)
            card_ids.add(listing_id)
            listing = self._parse_card(card, listing_id, urljoin(SITE_URL, href))
            if listing is not None:
                listings.append(listing)
        next_link = soup.select_one("a.paging__item.next")
        next_href = str(next_link.get("href", "")) if next_link is not None else ""
        next_url = urljoin(SITE_URL, next_href) if next_href else None
        return SearchPage(listings=listings, card_ids=card_ids, next_url=next_url)

    def _parse_card(self, card: Tag, listing_id: str, url: str) -> Listing | None:
        price_element = card.select_one("p.c-products__price strong")
        price = _price_of(price_element.get_text(" ", strip=True)) if price_element is not None else None
        if price is None:
            return None
        if self.criteria.max_price is not None and price > self.criteria.max_price:
            return None
        if self.criteria.min_price is not None and price < self.criteria.min_price:
            return None

        title_element = card.select_one("h2.c-products__title")
        raw_title = title_element.get_text() if title_element is not None else ""
        # The title starts with the offer in lowercase, which the page
        # capitalizes with CSS.
        title = " ".join(raw_title.split())
        title = title[:1].upper() + title[1:]
        disposition_match = DISPOSITION_RE.search(raw_title)
        first_area = _square_metres(AREA_RE.search(raw_title))
        # A plot's one area is its land; a building's is its own, followed
        # by its land ("domu 145 m² s pozemkem 6 115 m²").
        if self.criteria.estate_type == "land":
            size_m2, land_m2 = None, first_area
        else:
            size_m2, land_m2 = first_area, _square_metres(LAND_RE.search(raw_title))

        info_element = card.select_one("p.c-products__info")
        location = " ".join(info_element.get_text().split()) if info_element is not None else ""

        image = card.select_one(".c-products__img img[data-src]")
        image_url = str(image.get("data-src", "")) if image is not None else ""

        return Listing.build(
            id=f"idnes:{listing_id}",
            source="idnes",
            title=title,
            price=price,
            location_raw_text=location,
            parsed_place=parse_comma_separated_address(location),
            url=url,
            photo_urls=(image_url,) if image_url else (),
            gallery_on_advert_page=True,
            size_m2=size_m2,
            land_m2=land_m2,
            disposition_raw_text=disposition_match.group(1) if disposition_match else None,
        )
