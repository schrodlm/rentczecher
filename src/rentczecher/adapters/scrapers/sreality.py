import logging
import re
import time
import unicodedata

import requests

from rentczecher.adapters.scrapers.base import BaseScraper, Listing

log = logging.getLogger("rentczecher")

API_URL = "https://www.sreality.cz/api/v1/estates/search"
# The API silently clamps per_page to 100 and paginates by offset;
# the page param is silently ignored.
PER_PAGE = 100
# Hard bound so no server response pattern can cause an unbounded crawl.
MAX_PAGES = 50
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Selects the snake_case response shape; without it the API returns
    # camelCase page-hydration payloads.
    "Accept": "application/json",
}

OFFER_SEO = {1: "prodej", 2: "pronajem"}
CATEGORY_SEO = {1: "byt", 2: "dum", 3: "pozemek", 4: "komercni", 5: "ostatni"}


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").replace(" ", "-")


class SrealityScraper(BaseScraper):
    name = "sreality"

    def _build_params(self, offset: int) -> dict:
        cfg = self.scraper_cfg
        params = {
            "category_main_cb": cfg.get("category_main_cb", 1),
            "category_type_cb": cfg.get("category_type_cb", 2),
            "locality_district_id": cfg["locality_district_id"],
            "per_page": PER_PAGE,
            "offset": offset,
            "lang": "cs",
        }
        if self.max_price > 0:
            # The old czk_price_summary_order2=min|max param is silently
            # ignored by this API; price filtering happens client-side too.
            params["price_from"] = self.min_price
            params["price_to"] = self.max_price
        sub_cb = cfg.get("category_sub_cb")
        if sub_cb:
            # The API rejects the pipe syntax with HTTP 422; it wants the
            # parameter repeated, which requests produces from a list.
            params["category_sub_cb"] = [int(v) for v in str(sub_cb).split("|")]
        min_land = self.profile.get("search", {}).get("min_land_m2", 0)
        if min_land > 0:
            params["estate_area_from"] = min_land
        return params

    def scrape(self) -> list[Listing]:
        cfg = self.scraper_cfg
        if not cfg.get("enabled", False):
            return []
        if cfg.get("locality_district_id") is None:
            log.error(
                "sreality: locality_district_id is not configured for this "
                "profile - skipping scraper (refusing to silently search Praha 7)"
            )
            return []

        estates: dict[int, dict] = {}
        offset = 0
        for _ in range(MAX_PAGES):
            resp = requests.get(API_URL, params=self._build_params(offset), headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            known = len(estates)
            for estate in results:
                hash_id = estate.get("hash_id")
                if hash_id is not None:
                    estates.setdefault(hash_id, estate)
            total = data.get("pagination", {}).get("total", 0)
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

    def _parse_estate(self, estate: dict) -> Listing | None:
        hash_id = estate.get("hash_id")
        if hash_id is None:
            return None

        price = int(estate.get("price_czk") or estate.get("price") or 0)
        if self.max_price > 0 and (price > self.max_price or price < self.min_price):
            return None

        name = estate.get("advert_name", "")

        size = None
        size_match = re.search(r"(\d+)\s*m[2²]", name)
        if size_match:
            size = int(size_match.group(1))

        land = None
        land_match = re.search(r"pozemek\s+([\d\s]+)\s*m[2²]", name, re.IGNORECASE)
        if land_match:
            land = int(land_match.group(1).replace(" ", "").replace("\xa0", ""))

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
        cfg = self.scraper_cfg
        main_cb = (estate.get("category_main_cb") or {}).get("value") or cfg.get("category_main_cb", 1)
        type_cb = (estate.get("category_type_cb") or {}).get("value") or cfg.get("category_type_cb", 2)
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
