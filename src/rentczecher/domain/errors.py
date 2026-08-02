class ConfigError(Exception):
    """Invalid configuration, with a human-readable message naming the
    offending keys."""


class ConfigNotFoundError(ConfigError):
    """No config file exists at the resolved path."""
