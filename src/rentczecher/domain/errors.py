class ConfigError(Exception):
    """Invalid configuration, with a human-readable message naming the
    offending keys."""


class ConfigNotFoundError(ConfigError):
    """No config file exists at the resolved path."""


class ScraperBrokenError(Exception):
    """The portal responded, but not in the shape this scraper understands."""


class PlaceNotFoundError(Exception):
    def __init__(self, place: str, suggestions: tuple[str, ...]):
        self.place = place
        self.suggestions = suggestions
        hint = f" - did you mean: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"unknown place {place!r}{hint}")
