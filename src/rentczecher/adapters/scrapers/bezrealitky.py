import json
import re
import time

from dataclasses import dataclass

from rentczecher.adapters.scrapers.base import BaseScraper, Listing, ScraperBrokenError
from rentczecher.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher.domain.location import ParsedPlace

BASE_SEARCH_URL = "https://www.bezrealitky.cz/vyhledat"

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
    style dash pairs inside a segment; the portal has no district (okres)
    concept, so district is always None."""
    names = []
    for segment in address.split(","):
        for name in re.split(r"\s+[-–]\s+", segment):
            name = name.strip()
            if name and name not in names:
                names.append(name)
    return ParsedPlace(names=tuple(names))


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

    def __init__(self, spec, client):
        super().__init__(spec, client)
        self.place = BezrealitkyPlace.from_params(resolve(spec.place))

    def _build_url(self) -> str:
        params = [
            "currency=CZK",
            f"estateType={ESTATE_TYPE_PARAM[self.spec.estate_type]}",
            f"offerType={OFFER_TYPE_PARAM[self.spec.offer_type]}",
            f"regionOsmIds={self.place.region_id}",
            # The server applies search filters only when this param is
            # present; without it the page renders the place name but
            # serves unfiltered countrywide results.
            "location=exact",
        ]
        if self.spec.min_price > 0:
            params.append(f"priceFrom={self.spec.min_price}")
        if self.spec.max_price > 0:
            params.append(f"priceTo={self.spec.max_price}")
        return BASE_SEARCH_URL + "?" + "&".join(params)

    def scrape(self) -> list[Listing]:
        listings: list[Listing] = []
        page = 1
        while True:
            page_listings, total_count, page_had_adverts = self._parse_page(self._fetch_page(page))
            listings.extend(page_listings)
            if not page_had_adverts or page * 15 >= total_count:
                break
            page += 1
            time.sleep(1.5)

        return listings

    def _fetch_page(self, page: int) -> str:
        url = self._build_url()
        if page > 1:
            url += f"&page={page}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_page(self, html: str) -> tuple[list[Listing], int, bool]:
        """Return (listings, reported total count, whether the page carried any
        adverts before filtering)."""
        match = NEXT_DATA_RE.search(html)
        if not match:
            # Even an empty-result search page carries the Next.js hydration
            # blob; its absence means the page shape changed.
            raise ScraperBrokenError("bezrealitky: __NEXT_DATA__ payload missing from search page")

        next_data = json.loads(match.group(1))
        cache = next_data.get("props", {}).get("pageProps", {}).get("apolloCache", {})
        if not cache:
            return [], 0, False

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
            return [], 0, False

        listings = []
        page_had_adverts = False
        for ref in advert_list.get("list", []):
            ref_key = ref.get("__ref", "") if isinstance(ref, dict) else ""
            advert = cache.get(ref_key, {})
            if not advert:
                continue
            page_had_adverts = True
            listing = self._parse_advert(advert, cache)
            if listing is not None:
                listings.append(listing)

        return listings, total_count, page_had_adverts

    def _parse_advert(self, advert: dict, cache: dict) -> Listing | None:
        advert_id = advert.get("id", "")
        uri = advert.get("uri", "")
        price = advert.get("price", 0)

        if self.spec.max_price > 0 and price > self.spec.max_price:
            return None
        if price < self.spec.min_price:
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

        # Resolve main image
        image_url = None
        main_img_ref = advert.get("mainImage", {})
        if isinstance(main_img_ref, dict) and "__ref" in main_img_ref:
            img_obj = cache.get(main_img_ref["__ref"], {})
            image_url = _apollo_get(img_obj, "url")

        # Build title
        offer_label = "Pronajem" if OFFER_TYPE_PARAM[self.spec.offer_type] == "PRONAJEM" else "Prodej"
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
            location=address,
            parsed_place=_parse_location(address),
            url=f"{DETAIL_BASE}/{uri}",
            image_url=image_url,
            size_m2=int(float(surface)) if surface else None,
            disposition=disposition if disposition else None,
            lat=lat,
            lon=lon,
            charges=int(float(charges)) if charges else None,
            land_m2=int(float(surface_land)) if surface_land else None,
        )
