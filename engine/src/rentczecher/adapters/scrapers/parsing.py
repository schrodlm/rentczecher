import re

SIZE_M2_RE = re.compile(r"(\d+)\s*m[2²]")
LAND_M2_RE = re.compile(r"pozemek\s+([\d\s]+)\s*m[2²]", re.IGNORECASE)


def parse_size_m2(text: str) -> int | None:
    match = SIZE_M2_RE.search(text)
    return int(match.group(1)) if match else None


def parse_land_m2(text: str) -> int | None:
    match = LAND_M2_RE.search(text)
    if not match:
        return None
    return int(match.group(1).replace(" ", "").replace("\xa0", ""))
