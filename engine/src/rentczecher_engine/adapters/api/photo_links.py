import hashlib
import hmac


class PhotoLinks:
    """Signs a link to each stored photo with a secret made for this run of
    the engine, since an image request cannot carry the API's token. A link
    stays valid while the engine runs, and a restart invalidates every one."""

    def __init__(self, secret: bytes):
        self._secret = secret

    def link(self, file_key: str) -> str:
        return f"/v1/photos/{file_key}?sig={self._signature(file_key)}"

    def is_valid(self, file_key: str, signature: str) -> bool:
        return hmac.compare_digest(self._signature(file_key), signature)

    def _signature(self, file_key: str) -> str:
        return hmac.new(self._secret, file_key.encode(), hashlib.sha256).hexdigest()
