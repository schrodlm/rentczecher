from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ScraperHealth:
    status: Literal["ok", "broken", "zero_results"]
    error: str | None
    listing_count: int
