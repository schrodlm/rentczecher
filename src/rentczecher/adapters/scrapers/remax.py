import re
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from rentczecher.adapters.scrapers.base import BaseScraper, Listing
from rentczecher.adapters.scrapers.location_resolver import PlaceParams, resolve

SEARCH_BASE_URL = "https://www.remax-czech.cz/reality/vyhledavani/"

# Checkbox ids from the search form's types tree.
ESTATE_TYPE_IDS = {"flat": (4,), "house": (6,), "cottage": (10,), "land": (3,)}
OFFER_TYPE_ID = {"sale": 1, "rent": 2}


@dataclass(frozen=True, slots=True)
class RemaxPlace:
    region_id: int
    district_ids: tuple[int, ...]

    @classmethod
    def from_params(cls, place: PlaceParams) -> "RemaxPlace":
        (region_id, district_ids), = place.remax_regions.items()
        return cls(region_id=region_id, district_ids=district_ids)


class RemaxScraper(BaseScraper):
    name = "remax"

    def __init__(self, spec, client):
        super().__init__(spec, client)
        self.place = RemaxPlace.from_params(resolve(spec.place))

    def _build_url(self) -> str:
        query: list[tuple[str, object]] = [("hledani", OFFER_TYPE_ID[self.spec.offer_type])]
        query += [(f"types[{type_id}]", "on")
                  for type_id in ESTATE_TYPE_IDS[self.spec.estate_type]]
        query += [(f"regions[{self.place.region_id}][{district_id}]", "on")
                  for district_id in self.place.district_ids]
        if self.spec.min_price > 0:
            query.append(("price_from", self.spec.min_price))
        if self.spec.max_price > 0:
            query.append(("price_to", self.spec.max_price))
        return SEARCH_BASE_URL + "?" + urlencode(query)

    def scrape(self) -> list[Listing]:
        listings: list[Listing] = []
        page = 1
        while True:
            page_listings, has_next = self._parse_page(self._fetch_page(page))
            listings.extend(page_listings)
            if not page_listings or not has_next:
                break
            page += 1
            time.sleep(1.5)

        return listings

    def _fetch_page(self, page: int) -> str:
        url = self._build_url()
        if page > 1:
            url += f"&stranka={page}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_page(self, html: str) -> tuple[list[Listing], bool]:
        """Return (listings, whether a next-page link exists). A page without
        cards is indistinguishable from a genuinely empty search result, so it
        ends the crawl instead of raising."""
        soup = BeautifulSoup(html, "lxml")

        cards: list = soup.select("div.pl-items__item, article.property-card, div.card-property")
        if not cards:
            cards = self._find_listing_blocks(soup)
        if not cards:
            return [], False

        listings = []
        for card in cards:
            listing = self._parse_card(card)
            if listing:
                listings.append(listing)

        has_next = soup.select_one('a[rel="next"], a.pagination__next, li.next a') is not None
        return listings, has_next

    def _find_listing_blocks(self, soup: BeautifulSoup) -> list:
        blocks = []
        seen_links = set()
        for link in soup.find_all("a", href=re.compile(r"/reality/detail/\d+")):
            href = link.get("href", "")
            if href in seen_links:
                continue
            seen_links.add(href)
            parent = link.parent
            for _ in range(5):
                if parent and parent.name in ("div", "article", "li") and parent not in blocks:
                    text = parent.get_text()
                    if "Kc" in text or "Kč" in text or re.search(r"\d[\d\s]+Kc", text):
                        blocks.append(parent)
                        break
                if parent:
                    parent = parent.parent
        return blocks

    def _parse_card(self, card) -> Listing | None:
        link = card.find("a", href=re.compile(r"/reality/detail/\d+"))
        if not link:
            return None

        href = link.get("href", "")
        detail_url = href if href.startswith("http") else f"https://www.remax-czech.cz{href}"

        id_match = re.search(r"/detail/(\d+)", href)
        if not id_match:
            return None
        listing_id = id_match.group(1)

        # Prefer data-* attributes
        data_price = card.get("data-price")
        data_title = card.get("data-title")
        data_address = card.get("data-display-address")

        # Title
        title = ""
        if data_title:
            title = data_title
        else:
            title_el = card.find(["h2", "h3", "h4"]) or link
            if title_el:
                title = title_el.get_text(strip=True)
            title = re.sub(r"\s*\(ID\s+[^)]+\)\s*$", "", title)

        # Price
        price = 0
        if data_price:
            try:
                price = int(data_price)
            except ValueError:
                pass

        if not price:
            card_text = card.get_text()
            price_match = re.search(r"(\d[\d\s\xa0]*\d)\s*(?:Kc|Kč)", card_text)
            if not price_match:
                price_match = re.search(r"(\d)\s*(?:Kc|Kč)", card_text)
            if price_match:
                price_str = price_match.group(1).replace(" ", "").replace("\xa0", "")
                try:
                    price = int(price_str)
                except ValueError:
                    pass

        if self.spec.max_price > 0 and price > self.spec.max_price:
            return None
        if price < self.spec.min_price or price == 0:
            return None

        card_text = " ".join(card.get_text().split())  # Normalize whitespace

        # Location
        location = ""
        if data_address:
            location = " ".join(data_address.split())
        else:
            loc_match = re.search(r"(?:Praha\s*\d+\s*[-–]\s*\w+|[A-Z][a-záčďéěíňóřšťúůýž]+\s*[-–]\s*\w+)", card_text)
            if loc_match:
                location = loc_match.group(0)

        # Image
        image_url = None
        img = card.find("img")
        if img:
            image_url = img.get("src") or img.get("data-src")
            if image_url and not image_url.startswith("http"):
                image_url = f"https://www.remax-czech.cz{image_url}"

        # Size
        size = None
        size_match = re.search(r"(\d+)\s*m[2²]", card_text)
        if size_match:
            size = int(size_match.group(1))

        # Land area - "pozemek X m2" or "X m² pozemek"
        land = None
        land_match = re.search(r"pozemek\s+([\d\s]+)\s*m[2²]", card_text, re.IGNORECASE)
        if land_match:
            land = int(land_match.group(1).replace(" ", "").replace("\xa0", ""))

        # Disposition
        disposition = None
        disp_match = re.search(r"(\d\+(?:kk|1|\d))", card_text, re.IGNORECASE)
        if disp_match:
            disposition = disp_match.group(1)

        return Listing.build(
            id=f"remax:{listing_id}",
            source="remax",
            title=title or f"RE/MAX - {disposition or ''} {location}".strip(),
            price=price,
            location=location,
            url=detail_url,
            image_url=image_url,
            size_m2=size,
            disposition=disposition,
            land_m2=land,
        )
