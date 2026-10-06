"""The listing model: immutable scraped facts, immutable pipeline conclusions.

Facts change only when the world is re-observed (a new scrape constructs a
new ScrapedListing); conclusions change by replacement, never by mutation
(Listing.with_annotations returns a new Listing sharing the same facts).
"""

from dataclasses import dataclass, fields, replace

from rentczecher_engine.domain.disposition import Disposition, parse_disposition
from rentczecher_engine.domain.location import Location, ParsedPlace
from rentczecher_engine.domain.property import PropertyLocation


@dataclass(frozen=True, slots=True)
class ScrapedListing:
    id: str
    source: str
    title: str
    price: int
    location_raw_text: str
    url: str
    image_url: str | None = None
    size_m2: int | None = None
    disposition_raw_text: str | None = None
    lat: float | None = None
    lon: float | None = None
    charges: int | None = None
    land_m2: int | None = None
    scraped_at: str | None = None
    # The location text, parsed by the scraper, the only code that knows its
    # portal's format.
    parsed_place: ParsedPlace = ParsedPlace()


@dataclass(frozen=True, slots=True)
class ListingAnnotations:
    score: int = 0
    price_drop_from: int | None = None
    cross_source: tuple[str, ...] = ()
    resolved_location: Location | None = None


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
    def location_raw_text(self) -> str:
        return self.scraped.location_raw_text

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
    def disposition_raw_text(self) -> str | None:
        return self.scraped.disposition_raw_text

    @property
    def disposition(self) -> Disposition | None:
        return parse_disposition(self.scraped.disposition_raw_text)

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
    def cross_source(self) -> tuple[str, ...]:
        return self.annotations.cross_source

    @property
    def resolved_location(self) -> Location | None:
        return self.annotations.resolved_location


@dataclass(frozen=True, slots=True)
class SiblingSource:
    """Another portal's posting of the same property - the take-na badge."""

    source: str
    url: str


@dataclass(frozen=True, slots=True)
class InboxCard:
    """One listing as the GUI's inbox renders it: listing and property facts,
    this profile's tracking state, the latest observed price, a price-drop
    baseline when the previous observation was higher, and sibling postings
    of the same property on other portals.

    title/location_raw_text/size_m2/land_m2/disposition_raw_text/price are nullable: a card can exist
    before its property has facts or before any price was ever observed.
    property_location is None until a posting's text resolves to a place,
    and disposition is None when the property's text names no layout.
    """

    id: str
    source: str
    url: str
    title: str | None
    location_raw_text: str | None
    property_location: PropertyLocation | None
    size_m2: int | None
    land_m2: int | None
    disposition_raw_text: str | None
    disposition: Disposition | None
    first_seen_at: str
    viewed_at: str | None
    favourited_at: str | None
    price: int | None
    price_drop_from: int | None
    sibling_sources: tuple[SiblingSource, ...]
