class ConfigError(Exception):
    """Invalid configuration, with a human-readable message naming the
    offending keys."""


class ConfigNotFoundError(ConfigError):
    """No config file exists at the resolved path."""


class ScraperBrokenError(Exception):
    """The portal responded, but not in the shape this scraper understands."""


class PlaceNotFoundError(Exception):
    def __init__(self, place: str):
        super().__init__(f"unknown place {place!r}")


class AmbiguousPlaceError(Exception):
    def __init__(self, place: str):
        super().__init__(f"several places are called {place!r}")
