import json
import logging
import re
import time

from dataclasses import dataclass

from rentczecher_engine.adapters.scrapers.base import BaseScraper, Listing
from rentczecher_engine.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher_engine.domain.errors import ScraperBrokenError
from rentczecher_engine.domain.location import ParsedPlace

log = logging.getLogger("rentczecher")

BASE_SEARCH_URL = "https://www.bezrealitky.cz/vyhledat"
# Hard bound on one search's pages, so no pagination quirk can keep a scan
# reading the portal.
MAX_PAGES = 50
# The search serves 15 adverts a page.
PER_PAGE = 15

ESTATE_TYPE_PARAM = {"flat": "BYT", "house": "DUM", "land": "POZEMEK", "cottage": "REKREACNI_OBJEKT"}
OFFER_TYPE_PARAM = {"sale": "PRODEJ", "rent": "PRONAJEM"}

NEXT_DATA_RE = re.compile(
    r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
    re.DOTALL,
)

# Disposition enum -> human-readable
DISPOSITIONS = {
    "DISP_1_KK": "1+kk", "DISP_1_1": "1+1",
    "DISP_2_KK": "2+kk", "DISP_2_1": "2+1",
    "DISP_3_KK": "3+kk", "DISP_3_1": "3+1",
    "DISP_4_KK": "4+kk", "DISP_4_1": "4+1",
    "DISP_5_KK": "5+kk", "DISP_5_1": "5+1",
    "DISP_6": "6+", "DISP_OTHER": "atypicky",
    "GARSONIERA": "garsoniéra",
    "UNDEFINED": None,
}

DETAIL_BASE = "https://www.bezrealitky.cz/nemovitosti-byty-domy"


def _parse_location(address: str) -> ParsedPlace:
    """The portal's address string is comma-separated, with 'Praha - Bubeneč'
    style dash pairs inside a segment. An 'okres Domažlice' segment states
    the district."""
    names = []
    district = None
    for segment in address.split(","):
        for name in re.split(r"\s+[-–]\s+", segment):
            name = name.strip()
            if name.casefold().startswith("okres "):
                district = name[len("okres "):]
            elif name and name not in names:
                names.append(name)
    return ParsedPlace(names=tuple(names), district=district)


def _apollo_get(obj: dict, prefix: str):
    """Get value from Apollo cache key that may have parenthesized params."""
    for key, val in obj.items():
        if key == prefix or key.startswith(prefix + "("):
            return val
    return None


@dataclass(frozen=True, slots=True)
class BezrealitkyPlace:
    region_id: str

    @classmethod
    def from_params(cls, place: PlaceParams) -> "BezrealitkyPlace":
        return cls(region_id=place.bezrealitky_region_id)


class BezrealitkyScraper(BaseScraper):
    name = "bezrealitky"

    def __init__(self, criteria, client):
        super().__init__(criteria, client)
        self.place = BezrealitkyPlace.from_params(resolve(criteria.place))

    def _build_url(self) -> str:
        params = [
            "currency=CZK",
            f"estateType={ESTATE_TYPE_PARAM[self.criteria.estate_type]}",
            f"offerType={OFFER_TYPE_PARAM[self.criteria.offer_type]}",
            f"regionOsmIds={self.place.region_id}",
            # The server applies search filters only when this param is
            # present; without it the page renders the place name but
            # serves unfiltered countrywide results.
            "location=exact",
        ]
        if self.criteria.min_price is not None:
            params.append(f"priceFrom={self.criteria.min_price}")
        if self.criteria.max_price is not None:
            params.append(f"priceTo={self.criteria.max_price}")
        return BASE_SEARCH_URL + "?" + "&".join(params)

    def scrape(self) -> list[Listing]:
        listings: dict[str, Listing] = {}
        seen_adverts: set[str] = set()
        for page in range(1, MAX_PAGES + 1):
            page_listings, total_count, page_adverts = self._parse_page(self._fetch_page(page))
            for listing in page_listings:
                listings.setdefault(listing.id, listing)
            # A page of adverts already read means the portal is serving the
            # same page again, not that the search goes on. The adverts count
            # before filtering, since a page can carry adverts but no listing.
            repeated = page_adverts <= seen_adverts
            seen_adverts |= page_adverts
            if not page_adverts or page * PER_PAGE >= total_count or repeated:
                break
            time.sleep(1.5)
        else:
            log.warning("bezrealitky: pagination cap of %d pages reached - results may be incomplete", MAX_PAGES)

        return list(listings.values())

    def _fetch_page(self, page: int) -> str:
        url = self._build_url()
        if page > 1:
            url += f"&page={page}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_page(self, html: str) -> tuple[list[Listing], int, set[str]]:
        """Return (listings, reported total count, the cache keys of every
        advert the page carried before filtering)."""
        match = NEXT_DATA_RE.search(html)
        if not match:
            # Even an empty-result search page carries the Next.js hydration
            # blob; its absence means the page shape changed.
            raise ScraperBrokenError("bezrealitky: __NEXT_DATA__ payload missing from search page")

        next_data = json.loads(match.group(1))
        cache = next_data.get("props", {}).get("pageProps", {}).get("apolloCache", {})
        if not cache:
            return [], 0, set()

        # Find the listAdverts result
        advert_list = None
        total_count = 0
        for key, val in cache.items():
            if key.startswith("listAdverts(") or (isinstance(val, dict) and val.get("__typename") == "AdvertList"):
                if isinstance(val, dict) and "list" in val:
                    advert_list = val
                    total_count = val.get("totalCount", 0)
                    break

        root = cache.get("ROOT_QUERY", {})
        if not advert_list:
            for key, val in root.items():
                if key.startswith("listAdverts(") and isinstance(val, dict):
                    advert_list = val
                    total_count = val.get("totalCount", 0)
                    break

        if not advert_list:
            return [], 0, set()

        listings = []
        page_adverts: set[str] = set()
        for ref in advert_list.get("list", []):
            ref_key = ref.get("__ref", "") if isinstance(ref, dict) else ""
            advert = cache.get(ref_key, {})
            if not advert:
                continue
            page_adverts.add(ref_key)
            listing = self._parse_advert(advert, cache)
            if listing is not None:
                listings.append(listing)

        return listings, total_count, page_adverts

    def _parse_advert(self, advert: dict, cache: dict) -> Listing | None:
        advert_id = advert.get("id", "")
        uri = advert.get("uri", "")
        price = advert.get("price", 0)
        # The search asks for CZK and the portal converts nearly every advert,
        # but now and then one still comes back in its own currency, mostly
        # euros, whose number is not a price in crowns.
        if advert.get("currency") != "CZK":
            return None

        if self.criteria.max_price is not None and price > self.criteria.max_price:
            return None
        if self.criteria.min_price is not None and price < self.criteria.min_price:
            return None
        if advert.get("reserved", False):
            return None

        address = _apollo_get(advert, "address") or ""
        # Dereference Apollo ref if needed
        if isinstance(address, dict) and "__ref" in address:
            addr_obj = cache.get(address["__ref"], {})
            address = (_apollo_get(addr_obj, "presentationAddress")
                       or _apollo_get(addr_obj, "streetAddress")
                       or addr_obj.get("name", "") or "")
        if isinstance(address, dict):
            address = ""

        disposition_raw = advert.get("disposition", "")
        disposition = DISPOSITIONS.get(disposition_raw, disposition_raw or None)
        surface = advert.get("surface")
        surface_land = advert.get("surfaceLand")
        charges = advert.get("charges")

        # GPS (bezrealitky uses "lng" not "lon") - dereference __ref
        gps = advert.get("gps", {})
        if isinstance(gps, dict) and "__ref" in gps:
            gps = cache.get(gps["__ref"], {})
        lat = None
        lon = None
        if isinstance(gps, dict):
            lat = gps.get("lat")
            lon = gps.get("lng")

        # Resolve main photo
        main_photo_url = None
        main_img_ref = advert.get("mainImage", {})
        if isinstance(main_img_ref, dict) and "__ref" in main_img_ref:
            img_obj = cache.get(main_img_ref["__ref"], {})
            main_photo_url = _apollo_get(img_obj, "url")

        # Build title
        offer_label = "Pronajem" if OFFER_TYPE_PARAM[self.criteria.offer_type] == "PRONAJEM" else "Prodej"
        title_parts = [offer_label]
        if disposition:
            title_parts.append(disposition)
        if surface:
            title_parts.append(f"{surface} m2")
        if surface_land:
            title_parts.append(f"pozemek {surface_land} m2")
        if address:
            title_parts.append(address)
        title = " - ".join(title_parts)

        return Listing.build(
            id=f"bezrealitky:{advert_id}",
            source="bezrealitky",
            title=title,
            price=price,
            location_raw_text=address,
            parsed_place=_parse_location(address),
            url=f"{DETAIL_BASE}/{uri}",
            photo_urls=(main_photo_url,) if main_photo_url else (),
            gallery_on_advert_page=True,
            size_m2=int(float(surface)) if surface else None,
            disposition_raw_text=disposition if disposition else None,
            lat=lat,
            lon=lon,
            charges=int(float(charges)) if charges else None,
            land_m2=int(float(surface_land)) if surface_land else None,
        )
