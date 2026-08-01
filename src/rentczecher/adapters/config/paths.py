from pathlib import Path


def repo_root() -> Path:
    """Absolute path to the repository root.

    Resolves correctly only under an editable install, where the package
    lives in <root>/src/rentczecher/.
    """
    return Path(__file__).resolve().parents[4]
