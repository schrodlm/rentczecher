"""A listing's photos, and the gallery a tracked property shows."""

from dataclasses import dataclass
from typing import Literal

# A listing keeps at most its first this many photos.
GALLERY_LIMIT = 20
# A photo whose download failed this many times is given up.
MAX_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class FetchedPhoto:
    content: bytes
    media_type: str


@dataclass(frozen=True, slots=True)
class PendingPhoto:
    """A photo wanted but not stored yet."""

    property_id: str
    listing_id: str
    position: int
    source_url: str
    source: str


GalleryStatus = Literal["none", "downloading", "stored", "failed"]


@dataclass(frozen=True, slots=True)
class Gallery:
    """The gallery a tracked property shows, from its listing with the most
    photos."""

    source: str
    url: str
    photo_count: int
    file_keys: tuple[str, ...]
    status: GalleryStatus


def gallery_status(photo_count: int, stored: int, pending: int) -> GalleryStatus:
    if photo_count == 0:
        return "none"
    if pending > 0:
        return "downloading"
    if stored > 0:
        return "stored"
    return "failed"
