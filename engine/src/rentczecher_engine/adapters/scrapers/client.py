import httpx

# The app names itself and its site in every request. The version follows
# the package's, which a frozen build cannot read at runtime.
IDENTITY_HEADERS = {
    "User-Agent": "rentczecher/0.3.0 (+https://rentczecher.cz)",
}


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    # follow_redirects matches the requests behavior the scrapers were
    # built against; httpx does not follow redirects by default.
    # Transport retries cover connect failures only, not HTTP errors.
    return httpx.Client(
        headers=IDENTITY_HEADERS,
        timeout=30,
        follow_redirects=True,
        transport=transport if transport is not None else httpx.HTTPTransport(retries=3),
    )
