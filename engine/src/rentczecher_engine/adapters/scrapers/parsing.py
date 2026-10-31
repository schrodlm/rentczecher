import re

from rentczecher_engine.domain.location import ParsedPlace

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


def parse_comma_separated_address(address: str) -> ParsedPlace:
    """For a portal that writes an address as comma-separated segments, with
    'Praha - Bubeneč' style dash pairs inside a segment. An 'okres Domažlice'
    segment states the district."""
    names = []
    district = None
    for segment in address.split(","):
        for name in re.split(r"\s+[-–]\s+", segment):
            name = name.strip()
            if name.casefold().startswith("okres "):
                district = name[len("okres "):]
            elif name and name not in names:
                names.append(name)
    return ParsedPlace(names=tuple(names), district=district)
