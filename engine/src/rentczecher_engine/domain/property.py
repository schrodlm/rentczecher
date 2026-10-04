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
    location_raw_text: str | None = None
    size_m2: int | None = None
    disposition_raw_text: str | None = None
    lat: float | None = None
    lon: float | None = None
    land_m2: int | None = None


@dataclass(frozen=True, slots=True)
class PropertyLocation:
    """Where a property lies, as stored: the RÚIAN code of each unit, and
    its house numbers."""

    kraj_code: int
    okres_code: int | None
    obec_code: int | None
    obvod_code: int | None
    mestska_cast_code: int | None
    cast_obce_code: int | None
    ulice_code: int | None
    cislo_popisne: str | None
    cislo_orientacni: str | None

    def is_more_detailed_than(self, other: "PropertyLocation") -> bool:
        """A finer unit wins, and between equally fine ones a house number."""
        return self._coarseness() < other._coarseness()

    def _coarseness(self) -> tuple[int, bool]:
        codes_most_specific_first = (
            self.ulice_code, self.cast_obce_code, self.mestska_cast_code, self.obvod_code,
            self.obec_code, self.okres_code, self.kraj_code,
        )
        finest_rank = next(rank for rank, code in enumerate(codes_most_specific_first) if code is not None)
        has_no_house_number = self.cislo_popisne is None and self.cislo_orientacni is None
        return finest_rank, has_no_house_number
