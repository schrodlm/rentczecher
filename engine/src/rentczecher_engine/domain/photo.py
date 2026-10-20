"""A listing's photos."""

from dataclasses import dataclass

# A listing keeps at most its first this many photos.
GALLERY_LIMIT = 20


@dataclass(frozen=True, slots=True)
class FetchedPhoto:
    content: bytes
    media_type: str
