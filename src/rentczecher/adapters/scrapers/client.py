import httpx

# Sreality's API 404s requests without a browser User-Agent; the other
# portals tolerate it but a browser UA keeps all traffic uniform.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
}


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    # follow_redirects matches the requests behavior the scrapers were
    # built against; httpx does not follow redirects by default.
    return httpx.Client(
        headers=BROWSER_HEADERS,
        timeout=30,
        follow_redirects=True,
        transport=transport,
    )
