import logging
import time
import unicodedata
from dataclasses import dataclass

from rentczecher.adapters.scrapers.base import BaseScraper, Listing, ScraperBrokenError
from rentczecher.adapters.scrapers.location_resolver import PlaceParams, resolve
from rentczecher.adapters.scrapers.parsing import parse_land_m2, parse_size_m2
from rentczecher.domain.location import ParsedPlace

log = logging.getLogger("rentczecher")

API_URL = "https://www.sreality.cz/api/v1/estates/search"
# The API silently clamps per_page to 100 and paginates by offset;
# the page param is silently ignored.
PER_PAGE = 100
# Hard bound so no server response pattern can cause an unbounded crawl.
MAX_PAGES = 50
API_HEADERS = {
    # Selects the snake_case response shape; without it the API returns
    # camelCase page-hydration payloads.
    "Accept": "application/json",
}

OFFER_SEO = {1: "prodej", 2: "pronajem"}
CATEGORY_SEO = {1: "byt", 2: "dum", 3: "pozemek", 4: "komercni", 5: "ostatni"}

# Sreality has no separate top-level category for cottages; the portal
# lists them under houses.
ESTATE_TYPE_CB = {"flat": 1, "house": 2, "cottage": 2, "land": 3}
OFFER_TYPE_CB = {"sale": 1, "rent": 2}


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").replace(" ", "-")


def _parse_location(locality: dict) -> ParsedPlace:
    """The portal's "district" field is a city district ("Praha 7"), never an
    okres, so everything belongs in names."""
    names = []
    for key in ("street", "city", "citypart", "district"):
        value = (locality.get(key) or "").strip()
        if value and value not in names:
            names.append(value)
    return ParsedPlace(names=tuple(names))


@dataclass(frozen=True, slots=True)
class SrealityPlace:
    district_id: int | None
    region_id: int

    @classmethod
    def from_params(cls, place: PlaceParams) -> "SrealityPlace":
        return cls(district_id=place.sreality_district_id,
                   region_id=place.sreality_region_id)


class SrealityScraper(BaseScraper):
    name = "sreality"

    def __init__(self, spec, client):
        super().__init__(spec, client)
        self.place = SrealityPlace.from_params(resolve(spec.place))

    def _category_cbs(self) -> tuple[int, int]:
        return ESTATE_TYPE_CB[self.spec.estate_type], OFFER_TYPE_CB[self.spec.offer_type]

    def _location_params(self) -> dict:
        if self.place.district_id is not None:
            return {"locality_district_id": self.place.district_id}
        return {"locality_region_id": self.place.region_id}

    def _build_params(self, offset: int) -> dict:
        main_cb, type_cb = self._category_cbs()
        params = {
            "category_main_cb": main_cb,
            "category_type_cb": type_cb,
            **self._location_params(),
            "per_page": PER_PAGE,
            "offset": offset,
            "lang": "cs",
        }
        if self.spec.max_price > 0:
            # The old czk_price_summary_order2=min|max param is silently
            # ignored by this API; price filtering happens client-side too.
            params["price_from"] = self.spec.min_price
            params["price_to"] = self.spec.max_price
        if self.spec.min_land_m2 > 0:
            params["estate_area_from"] = self.spec.min_land_m2
        return params

    def scrape(self) -> list[Listing]:
        estates: dict[int, dict] = {}
        offset = 0
        for _ in range(MAX_PAGES):
            data = self._fetch_page(offset)
            results = data["results"]
            known = len(estates)
            for estate in results:
                hash_id = estate.get("hash_id")
                if hash_id is not None:
                    estates.setdefault(hash_id, estate)
            total = data["pagination"].get("total", 0)
            made_progress = len(estates) > known
            if not results or len(estates) >= total or not made_progress:
                break
            offset += PER_PAGE
            time.sleep(1)
        else:
            log.warning("sreality: pagination cap of %d pages reached - results may be incomplete", MAX_PAGES)

        listings = []
        for estate in estates.values():
            listing = self._parse_estate(estate)
            if listing is not None:
                listings.append(listing)
        return listings

    def _fetch_page(self, offset: int) -> dict:
        resp = self._client.get(API_URL, params=self._build_params(offset), headers=API_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or "results" not in data or "pagination" not in data:
            raise ScraperBrokenError("sreality: search response is missing results/pagination")
        return data

    def _parse_estate(self, estate: dict) -> Listing | None:
        hash_id = estate.get("hash_id")
        if hash_id is None:
            return None

        price = int(estate.get("price_czk") or estate.get("price") or 0)
        if self.spec.max_price > 0 and (price > self.spec.max_price or price < self.spec.min_price):
            return None

        name = estate.get("advert_name", "")
        size = parse_size_m2(name)
        land = parse_land_m2(name)

        # category_sub_cb names the flat's layout ("2+kk") but a house's
        # building subtype ("Rodinný"); a house's real layout appears only in
        # the advert title, unextracted.
        sub_cb = estate.get("category_sub_cb") or {}
        disposition = sub_cb.get("name") or None

        locality = estate.get("locality") or {}
        location = self._compose_location(locality)
        lat = locality.get("gps_lat")
        lon = locality.get("gps_lon")

        images = estate.get("advert_images") or []
        image_url = None
        if images:
            image_url = images[0]
            if image_url.startswith("//"):
                image_url = f"https:{image_url}"

        return Listing.build(
            id=f"sreality:{hash_id}",
            source="sreality",
            title=name,
            price=price,
            location=location,
            parsed_place=_parse_location(locality),
            url=self._build_detail_url(estate, hash_id, disposition, locality),
            image_url=image_url,
            size_m2=size,
            disposition=disposition,
            lat=lat,
            lon=lon,
            land_m2=land,
        )

    @staticmethod
    def _compose_location(locality: dict) -> str:
        city = locality.get("city") or ""
        citypart = locality.get("citypart") or ""
        street = locality.get("street") or ""
        district = locality.get("district") or ""

        base = f"{city} - {citypart}" if citypart and citypart != city else city
        parts = [street, base]
        if district and district not in base:
            parts.append(district)
        return ", ".join(p for p in parts if p)

    def _build_detail_url(self, estate: dict, hash_id: int, disposition: str | None, locality: dict) -> str:
        default_main_cb, default_type_cb = self._category_cbs()
        main_cb = (estate.get("category_main_cb") or {}).get("value") or default_main_cb
        type_cb = (estate.get("category_type_cb") or {}).get("value") or default_type_cb
        offer_seo = OFFER_SEO.get(type_cb, "prodej")
        category_seo = CATEGORY_SEO.get(main_cb, "byt")
        sub_seo = _slugify(disposition) if disposition else ""
        locality_seo = "-".join(
            p for p in (
                locality.get("city_seo_name"),
                locality.get("citypart_seo_name"),
                locality.get("street_seo_name"),
            ) if p
        )
        segments = [s for s in (offer_seo, category_seo, sub_seo, locality_seo, str(hash_id)) if s]
        return "https://www.sreality.cz/detail/" + "/".join(segments)
