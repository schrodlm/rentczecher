import os
import re
import time
from pathlib import Path
from uuid import uuid4

# The image types a photo is kept in, and the extension its file carries.
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MEDIA_TYPES = {extension: media_type for media_type, extension in EXTENSIONS.items()}

_FILE_KEY = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")
_PARTIAL_SUFFIX = ".part"


class FilePhotoStore:
    """Photo files in one folder, each named by its key: a random name and
    the extension of its image type. A key is checked before it becomes a
    path, so no key can reach outside the folder."""

    def __init__(self, root: Path):
        self._root = root

    def put(self, content: bytes, media_type: str) -> str:
        """Written under a temporary name and renamed into place, so a crash
        never leaves a half-written photo under a key."""
        file_key = uuid4().hex + EXTENSIONS[media_type]
        path = self.path(file_key)
        self._root.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + _PARTIAL_SUFFIX)
        partial.write_bytes(content)
        os.replace(partial, path)
        return file_key

    def path(self, file_key: str) -> Path:
        if not _FILE_KEY.fullmatch(file_key):
            raise ValueError(f"not a photo key: {file_key!r}")
        return self._root / file_key

    def delete(self, file_key: str) -> None:
        self.path(file_key).unlink(missing_ok=True)

    def file_keys(self, older_than_s: float) -> set[str]:
        """The keys of the files written more than older_than_s ago."""
        if not self._root.is_dir():
            return set()
        written_before = time.time() - older_than_s
        return {
            path.name for path in self._root.iterdir()
            if _FILE_KEY.fullmatch(path.name) and path.stat().st_mtime < written_before
        }

    def remove_partials(self) -> None:
        """Deletes the files a crash left half-written."""
        if not self._root.is_dir():
            return
        for path in self._root.iterdir():
            if path.name.endswith(_PARTIAL_SUFFIX):
                path.unlink(missing_ok=True)


def media_type_of(file_key: str) -> str:
    return MEDIA_TYPES[Path(file_key).suffix]
