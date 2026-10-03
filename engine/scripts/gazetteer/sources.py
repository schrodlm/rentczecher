"""Downloads the two RÚIAN files the gazetteer is built from. ČÚZK publishes
both monthly, dated the last day of the previous month."""

import re
from pathlib import Path

import httpx

DOWNLOAD_PAGE = "https://nahlizenidokn.cuzk.gov.cz/StahniAdresniMistaRUIAN.aspx"
_ADDRESS_DUMP_LINK = re.compile(r'href="(https://[^"]*/(\d{8})_OB_ADR_csv\.zip)"')
# The state file is not linked from the download page. It is published in
# the exchange-format directory under the address dump's date.
STATE_FILE_URL = "https://vdp.cuzk.gov.cz/vymenny_format/soucasna/{date}_ST_UZSZ.xml.zip"


def download_sources(dest: Path) -> tuple[Path, Path]:
    """The current state file and address dump, downloaded into dest."""
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        page = client.get(DOWNLOAD_PAGE)
        page.raise_for_status()
        match = _ADDRESS_DUMP_LINK.search(page.text)
        if match is None:
            raise SystemExit("ruian: no OB_ADR_csv.zip link on the download page, has its shape changed?")
        dump_url, date = match.groups()
        state_file = dest / f"{date}_ST_UZSZ.xml.zip"
        address_dump = dest / f"{date}_OB_ADR_csv.zip"
        _download(client, STATE_FILE_URL.format(date=date), state_file)
        _download(client, dump_url, address_dump)
    return state_file, address_dump


def _download(client: httpx.Client, url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    with client.stream("GET", url) as response, open(dest, "wb") as out:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            out.write(chunk)
    print(f"  {dest.stat().st_size / 1e6:.0f} MB")
