import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from rentczecher_engine.adapters.scrapers.base import BaseScraper, Listing
from rentczecher_engine.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher_engine.adapters.scrapers.parsing import parse_land_m2, parse_size_m2
from rentczecher_engine.domain.location import ParsedPlace

log = logging.getLogger("rentczecher")

SEARCH_BASE_URL = "https://www.remax-czech.cz/reality/vyhledavani/"
# Hard bound on one search's pages, so no pagination quirk can keep a scan
# reading the portal.
MAX_PAGES = 50

# Checkbox ids from the search form's types tree.
ESTATE_TYPE_IDS = {"flat": (4,), "house": (6,), "cottage": (10,), "land": (3,)}
# The form's offer type radio is named "sale", 1 selling and 2 renting. Its
# "hledani" radio only switches between the list and the map, and 1 is the
# list the cards are read from.
SALE_VALUE = {"sale": 1, "rent": 2}
LIST_VIEW = 1

DETAIL_PATH = re.compile(r"/reality/detail/(\d+)")


_HOUSE_NUMBERS = re.compile(r"(\d+[a-zA-Z]?)\s*/\s*(\d+[a-zA-Z]?)$")


def _house_numbers(street_slot: str) -> tuple[str | None, str | None]:
    """The číslo popisné and číslo orientační ending the street slot. The
    portal repeats the popisné when there is no orientační
    ("U smaltovny 1419 / 1419"). A lone number is skipped, since it could be
    either."""
    match = _HOUSE_NUMBERS.search(street_slot)
    if match is None:
        return None, None
    popisne, orientacni = match.group(1), match.group(2)
    if orientacni == popisne:
        return popisne, None
    return popisne, orientacni


def _price_of(text: str, area_m2: int | None) -> int:
    """The whole property's price a card's price field states, or 0 when it
    states none. The field is formatted ('16 500 Kč (za měsíc)'), with the
    price's unit in brackets after the currency. A plot may be priced per m²
    of the area the card names, a rent may be yearly, which no monthly rent
    compares with, and a rented flat's card says 'Pronajato' instead."""
    amount, _, unit = text.partition("Kč")
    digits = re.sub(r"\D", "", amount)
    if not digits:
        return 0
    if "za m²" in unit:
        return int(digits) * area_m2 if area_m2 is not None else 0
    if "za rok" in unit:
        return 0
    return int(digits)


def _names_kraj(segment: str) -> bool:
    """'Karlovarský kraj' and 'Kraj Vysočina' name the kraj, which the
    address adds after everything finer."""
    folded = segment.casefold()
    return folded.endswith("kraj") or folded.startswith("kraj ")


# A Praha address names the capital in both the okres and the kraj slot:
# 'Rybná , Hlavní město Praha , Praha 1, Hlavní město Praha'.
_PRAHA = "hlavní město praha"


def _parse_location(location: str, title: str) -> ParsedPlace:
    """The address slot before the kraj holds the okres, not the town - a
    property labeled 'Domažlice' may lie anywhere in that district. Praha
    listings are the exception (their slot holds a city district like
    'Praha 4'), and a slot with digits is a street, not an okres. The town
    itself rides at the tail of the card title ('Prodej bytu 60 m², Aš');
    a tail equal to the okres means the property sits in the district
    capital, and the town then says everything the okres would."""
    names: list[str] = []
    district = None
    segments = [s.strip() for s in location.split(",") if s.strip()]
    in_praha = any(segment.casefold() == _PRAHA for segment in segments)
    segments = [segment for segment in segments if segment.casefold() != _PRAHA]
    for at, segment in enumerate(segments):
        if _names_kraj(segment):
            continue
        head, *tail = (part.strip() for part in re.split(r"\s+[-–]\s+", segment))
        is_last_bare_slot = at == len(segments) - 1 or _names_kraj(segments[at + 1])
        if (is_last_bare_slot and district is None and not in_praha
                and head != "Praha" and not any(ch.isdigit() for ch in head)):
            district = head
        elif head not in names:
            names.append(head)
        names.extend(part for part in tail if part and part not in names)
    town = title.rpartition(",")[2].strip() if "," in title else ""
    if town and not any(ch.isdigit() for ch in town):
        if district is not None and town.casefold() == district.casefold():
            district = None
        if town not in names:
            names.append(town)
    cislo_popisne, cislo_orientacni = _house_numbers(segments[0]) if segments else (None, None)
    return ParsedPlace(names=tuple(names), district=district,
                       cislo_popisne=cislo_popisne, cislo_orientacni=cislo_orientacni)


@dataclass(frozen=True, slots=True)
class RemaxPlace:
    region_id: int
    district_ids: tuple[int, ...]

    @classmethod
    def from_params(cls, place: PlaceParams) -> "RemaxPlace":
        (region_id, district_ids), = place.remax_regions.items()
        return cls(region_id=region_id, district_ids=district_ids)


@dataclass(frozen=True, slots=True)
class DetailLink:
    element: Tag
    href: str
    listing_id: str


def _detail_link(card: Tag) -> DetailLink | None:
    """None for a card without a detail link."""
    element = card.find("a", href=DETAIL_PATH)
    if not isinstance(element, Tag):
        return None
    href = str(element.get("href", ""))
    match = DETAIL_PATH.search(href)
    if match is None:
        return None
    return DetailLink(element=element, href=href, listing_id=match.group(1))


class RemaxScraper(BaseScraper):
    name = "remax"

    def __init__(self, criteria, client):
        super().__init__(criteria, client)
        self.place = RemaxPlace.from_params(resolve(criteria.place))

    def _build_url(self) -> str:
        query: list[tuple[str, object]] = [("hledani", LIST_VIEW), ("sale", SALE_VALUE[self.criteria.offer_type])]
        query += [(f"types[{type_id}]", "on")
                  for type_id in ESTATE_TYPE_IDS[self.criteria.estate_type]]
        query += [(f"regions[{self.place.region_id}][{district_id}]", "on")
                  for district_id in self.place.district_ids]
        if self.criteria.min_price is not None:
            query.append(("price_from", self.criteria.min_price))
        if self.criteria.max_price is not None:
            query.append(("price_to", self.criteria.max_price))
        return SEARCH_BASE_URL + "?" + urlencode(query)

    def scrape(self) -> list[Listing]:
        listings: dict[str, Listing] = {}
        seen_card_ids: set[str] = set()
        for page in range(1, MAX_PAGES + 1):
            page_listings, has_next, page_card_ids = self._parse_page(self._fetch_page(page))
            for listing in page_listings:
                listings.setdefault(listing.id, listing)
            # A page of cards already read means the portal is serving the
            # same page again, not that the search goes on. The cards count
            # before filtering, since a page can carry cards but no listing.
            repeated = page_card_ids <= seen_card_ids
            seen_card_ids |= page_card_ids
            if not page_card_ids or not has_next or repeated:
                break
            time.sleep(1.5)
        else:
            log.warning("remax: pagination cap of %d pages reached - results may be incomplete", MAX_PAGES)

        return list(listings.values())

    def _fetch_page(self, page: int) -> str:
        url = self._build_url()
        if page > 1:
            url += f"&stranka={page}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_page(self, html: str) -> tuple[list[Listing], bool, set[str]]:
        """Return (listings, whether a next-page link exists, the detail ids
        of every card with a detail link, before filtering). A page without cards is
        indistinguishable from a genuinely empty search result, so it ends the
        paging instead of raising."""
        soup = BeautifulSoup(html, "lxml")

        cards: list = soup.select("div.pl-items__item")
        if not cards:
            return [], False, set()

        listings = []
        card_ids: set[str] = set()
        for card in cards:
            detail = _detail_link(card)
            if detail is None:
                continue
            card_ids.add(detail.listing_id)
            listing = self._parse_card(card, detail)
            if listing:
                listings.append(listing)

        has_next = soup.select_one('a[rel="next"], a.pagination__next, li.next a') is not None
        return listings, has_next, card_ids

    def _parse_card(self, card, detail: DetailLink) -> Listing | None:
        href = detail.href
        detail_url = href if href.startswith("http") else f"https://www.remax-czech.cz{href}"

        # Prefer data-* attributes
        data_price = card.get("data-price")
        data_title = card.get("data-title")
        data_address = card.get("data-display-address")

        # Title
        title = ""
        if data_title:
            title = data_title
        else:
            title_el = card.find(["h2", "h3", "h4"]) or detail.element
            if title_el:
                title = title_el.get_text(strip=True)
            title = re.sub(r"\s*\(ID\s+[^)]+\)\s*$", "", title)

        card_text = " ".join(card.get_text().split())  # Normalize whitespace
        size = parse_size_m2(card_text)
        land = parse_land_m2(card_text)

        # Price
        price = _price_of(data_price or "", land if land is not None else size)
        if price == 0:
            return None
        if self.criteria.max_price is not None and price > self.criteria.max_price:
            return None
        if self.criteria.min_price is not None and price < self.criteria.min_price:
            return None

        # Location
        location = ""
        if data_address:
            location = " ".join(data_address.split())
        else:
            loc_match = re.search(r"(?:Praha\s*\d+\s*[-–]\s*\w+|[A-Z][a-záčďéěíňóřšťúůýž]+\s*[-–]\s*\w+)", card_text)
            if loc_match:
                location = loc_match.group(0)
        parsed_place = _parse_location(location, title)

        # Main photo
        main_photo_url = None
        img = card.find("img")
        if img:
            main_photo_url = img.get("src") or img.get("data-src")
            if main_photo_url and not main_photo_url.startswith("http"):
                main_photo_url = f"https://www.remax-czech.cz{main_photo_url}"

        # Disposition
        disposition = None
        disp_match = re.search(r"(\d\+(?:kk|1|\d))", card_text, re.IGNORECASE)
        if disp_match:
            disposition = disp_match.group(1)

        return Listing.build(
            id=f"remax:{detail.listing_id}",
            source="remax",
            title=title or f"RE/MAX - {disposition or ''} {location}".strip(),
            price=price,
            location_raw_text=location,
            parsed_place=parsed_place,
            url=detail_url,
            photo_urls=(main_photo_url,) if main_photo_url else (),
            size_m2=size,
            disposition_raw_text=disposition,
            land_m2=land,
        )
