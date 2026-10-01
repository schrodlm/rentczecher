from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchSpec:
    """Portal-neutral search intent; scrapers translate it into their
    portal's own parameters."""

    offer_type: str
    estate_type: str
    place: str
    min_price: int = 0
    max_price: int = 0
    min_size_m2: int = 0
    min_land_m2: int = 0
    dispositions: tuple[str, ...] = ()

    @classmethod
    def from_search_config(cls, search: dict) -> "SearchSpec":
        return cls(
            offer_type=search["offer_type"],
            estate_type=search["estate_type"],
            place=search["place"],
            min_price=search.get("min_price", 0),
            max_price=search.get("max_price", 0),
            min_size_m2=search.get("min_size_m2", 0),
            min_land_m2=search.get("min_land_m2", 0),
            dispositions=tuple(search.get("dispositions", ())),
        )
