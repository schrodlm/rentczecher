"""Profiles, search criteria and scoring preferences for tests: a plain
rent/flat search of obvod Praha 7 with no bounds, every preference off unless
a test turns it on, and an enabled profile scanning sreality with both."""

from dataclasses import replace

from rentczecher_engine.domain.disposition import Disposition, parse_disposition
from rentczecher_engine.domain.location import PlaceRef
from rentczecher_engine.domain.profile import Criteria, Preferences, Profile


def criteria(**overrides) -> Criteria:
    defaults = Criteria(offer_type="rent", estate_type="flat", place=PlaceRef("obvod", 78))
    return replace(defaults, **overrides)


def preferences(**overrides) -> Preferences:
    defaults = Preferences(
        price_per_m2_weight=0, disposition_weight=0, preferred_dispositions=(),
        size_weight=0, ideal_size_m2=None, place_weight=0, preferred_places=(),
        land_weight=0, ideal_land_m2=None, price_weight=0, max_good_price=None,
    )
    return replace(defaults, **overrides)


def profile(**overrides) -> Profile:
    defaults = Profile(
        id="p", name="P", enabled=True, portals=("sreality",),
        criteria=criteria(), preferences=preferences(),
    )
    return replace(defaults, **overrides)


def layouts(*codes: str) -> tuple[Disposition, ...]:
    parsed = []
    for code in codes:
        layout = parse_disposition(code)
        assert layout is not None
        parsed.append(layout)
    return tuple(parsed)
