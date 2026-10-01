"""Channel-agnostic notification content, assembled once per run and handed
to whichever Notifier is configured to send it.

Pure content: no HTML, no transport. A channel's own adapter decides how to
render this into an email, a push message, or anything else.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from rentczecher.domain.listing import DisappearedListing, Listing
from rentczecher.domain.search import SearchSpec
from rentczecher.services.diff import DiffResult


@dataclass(frozen=True, slots=True)
class Notification:
    profile_name: str
    subject: str
    is_rent: bool
    listings: tuple[Listing, ...]
    disappeared: tuple[DisappearedListing, ...]


@runtime_checkable
class Notifier(Protocol):
    def send(self, notification: Notification) -> bool:
        ...


def _subject(new_count: int, drop_count: int, profile_name: str) -> str:
    parts = []
    if new_count:
        parts.append(f"{new_count} nových nabídek")
    if drop_count:
        parts.append(f"{drop_count} slev")
    return f"{profile_name}: {', '.join(parts)}"


def build_notification(diff: DiffResult, profile_config: dict, spec: SearchSpec) -> Notification:
    listings = sorted(diff.new + diff.price_drops, key=lambda listing: listing.score, reverse=True)
    new_count = len(diff.new)
    drop_count = len(diff.price_drops)
    profile_name = profile_config.get("name", "Byt Watchdog")
    return Notification(
        profile_name=profile_name,
        subject=_subject(new_count, drop_count, profile_name),
        is_rent=spec.offer_type == "rent",
        listings=tuple(listings),
        disappeared=tuple(diff.disappeared),
    )
