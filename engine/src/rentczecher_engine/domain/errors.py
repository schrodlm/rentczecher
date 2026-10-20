class ScraperBrokenError(Exception):
    """The portal responded, but not in the shape this scraper understands."""


class PlaceNotFoundError(Exception):
    def __init__(self, place: str):
        super().__init__(f"unknown place {place!r}")


class ProfileNotFoundError(Exception):
    def __init__(self, profile_id: str):
        super().__init__(f"unknown profile {profile_id!r}")


class AmbiguousPlaceError(Exception):
    def __init__(self, place: str):
        super().__init__(f"several places are called {place!r}")


class PhotoRefusedError(Exception):
    """The portal's server refused the app a photo or an advert page."""


class PhotoGoneError(Exception):
    """The photo or the advert page is gone, or its URL is malformed."""


class PhotoFetchError(Exception):
    """The photo or the advert page could not be fetched this time."""
