"""The listing model: immutable scraped facts, immutable pipeline conclusions.

Facts change only when the world is re-observed (a new scrape constructs a
new ScrapedListing); conclusions change by replacement, never by mutation
(Listing.with_annotations returns a new Listing sharing the same facts).
"""

from dataclasses import dataclass, fields, replace

from rentczecher.domain.location import ParsedPlace


@dataclass(frozen=True, slots=True)
class ScrapedListing:
    id: str
    source: str
    title: str
    price: int
    location: str
    url: str
    image_url: str | None = None
    size_m2: int | None = None
    disposition: str | None = None
    lat: float | None = None
    lon: float | None = None
    charges: int | None = None
    land_m2: int | None = None
    scraped_at: str | None = None
    # location, parsed into place names by the scraper - the only code
    # that knows its portal's format.
    parsed_place: ParsedPlace = ParsedPlace()


@dataclass(frozen=True, slots=True)
class ListingAnnotations:
    score: int = 0
    price_drop_from: int | None = None
    nearest_stop: str | None = None
    stop_distance_m: int | None = None
    cross_source: tuple[str, ...] = ()


_SCRAPED_FIELDS = frozenset(f.name for f in fields(ScrapedListing))
_ANNOTATION_FIELDS = frozenset(f.name for f in fields(ListingAnnotations))


@dataclass(frozen=True, slots=True)
class Listing:
    scraped: ScrapedListing
    annotations: ListingAnnotations = ListingAnnotations()

    @classmethod
    def build(cls, **kwargs) -> "Listing":
        """Construct from flat field names, splitting facts from annotations."""
        unknown = set(kwargs) - _SCRAPED_FIELDS - _ANNOTATION_FIELDS
        if unknown:
            raise TypeError(f"unknown listing fields: {sorted(unknown)}")
        scraped = {k: v for k, v in kwargs.items() if k in _SCRAPED_FIELDS}
        annotations = {k: v for k, v in kwargs.items() if k in _ANNOTATION_FIELDS}
        return cls(ScrapedListing(**scraped), ListingAnnotations(**annotations))

    def with_annotations(self, **changes) -> "Listing":
        return replace(self, annotations=replace(self.annotations, **changes))

    @property
    def id(self) -> str:
        return self.scraped.id

    @property
    def source(self) -> str:
        return self.scraped.source

    @property
    def title(self) -> str:
        return self.scraped.title

    @property
    def price(self) -> int:
        return self.scraped.price

    @property
    def location(self) -> str:
        return self.scraped.location

    @property
    def url(self) -> str:
        return self.scraped.url

    @property
    def image_url(self) -> str | None:
        return self.scraped.image_url

    @property
    def size_m2(self) -> int | None:
        return self.scraped.size_m2

    @property
    def disposition(self) -> str | None:
        return self.scraped.disposition

    @property
    def lat(self) -> float | None:
        return self.scraped.lat

    @property
    def lon(self) -> float | None:
        return self.scraped.lon

    @property
    def charges(self) -> int | None:
        return self.scraped.charges

    @property
    def land_m2(self) -> int | None:
        return self.scraped.land_m2

    @property
    def scraped_at(self) -> str | None:
        return self.scraped.scraped_at

    @property
    def parsed_place(self) -> ParsedPlace:
        return self.scraped.parsed_place

    @property
    def score(self) -> int:
        return self.annotations.score

    @property
    def price_drop_from(self) -> int | None:
        return self.annotations.price_drop_from

    @property
    def nearest_stop(self) -> str | None:
        return self.annotations.nearest_stop

    @property
    def stop_distance_m(self) -> int | None:
        return self.annotations.stop_distance_m

    @property
    def cross_source(self) -> tuple[str, ...]:
        return self.annotations.cross_source
