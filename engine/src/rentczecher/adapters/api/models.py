"""Pydantic response models for the sidecar API: the single source of truth
for the wire contract.

The chain runs one way. These classes generate the OpenAPI schema (a
language-neutral JSON description of every endpoint and shape), and the
GUI's TypeScript types are generated from that schema. Python is never
generated from anything, it is the origin. A field renamed here is
therefore a contract change the GUI is rebuilt against, not an internal
refactor."""

from typing import Literal

from pydantic import BaseModel

from rentczecher.adapters.api.run_manager import PortalHealthEntry
from rentczecher.domain.listing import InboxCard


class ProfileModel(BaseModel):
    id: str
    name: str
    enabled: bool

    @classmethod
    def from_config(cls, profile_id: str, profile_config: dict) -> "ProfileModel":
        return cls(
            id=profile_id,
            name=profile_config["name"],
            enabled=profile_config.get("enabled", True),
        )


class SiblingSourceModel(BaseModel):
    source: str
    url: str


class ListingModel(BaseModel):
    id: str
    source: str
    url: str
    title: str | None
    location: str | None
    size_m2: int | None
    disposition: str | None
    first_seen_at: str
    viewed_at: str | None
    favourited_at: str | None
    price: int | None
    price_drop_from: int | None
    sibling_sources: list[SiblingSourceModel]

    @classmethod
    def from_card(cls, card: InboxCard) -> "ListingModel":
        return cls(
            id=card.id,
            source=card.source,
            url=card.url,
            title=card.title,
            location=card.location,
            size_m2=card.size_m2,
            disposition=card.disposition,
            first_seen_at=card.first_seen_at,
            viewed_at=card.viewed_at,
            favourited_at=card.favourited_at,
            price=card.price,
            price_drop_from=card.price_drop_from,
            sibling_sources=[
                SiblingSourceModel(source=sibling.source, url=sibling.url)
                for sibling in card.sibling_sources
            ],
        )


class RunTriggeredModel(BaseModel):
    run_id: str
    profile_id: str


class PortalHealthModel(BaseModel):
    portal: str
    status: Literal["ok", "broken", "zero_results"]
    error: str | None
    listing_count: int
    checked_at: str

    @classmethod
    def from_entry(cls, portal: str, entry: PortalHealthEntry) -> "PortalHealthModel":
        return cls(
            portal=portal, status=entry.status, error=entry.error,
            listing_count=entry.listing_count, checked_at=entry.checked_at,
        )
