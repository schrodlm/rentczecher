from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PropertyIdentity:
    """A property row: the inferred real-world unit and its canonical facts.

    Facts are seeded from the first listing to create the property.
    """

    id: str
    created_at: str
    merged_into: str | None = None
    title: str | None = None
    location: str | None = None
    size_m2: int | None = None
    disposition: str | None = None
    lat: float | None = None
    lon: float | None = None
    land_m2: int | None = None
