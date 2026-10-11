"""Scenarios: named stories of scans and user actions, replayed through the
engine into a fresh data folder.

A scenario file states what happened, never what the database looks like:
the listings each scan saw, then what the user did. Replaying it runs the
engine's own pipeline with faked scrapers and a controlled clock, so the
resulting database is exactly what real scans would have left, and schema
changes leave scenario files untouched.

The replay also writes the panel's user config, so the app opens set up. A
scenario may state its theme and language, or say first-run to leave the
config out and open on the welcome wizard.
"""

import json
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import get_args

import yaml

from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.profiles import SqliteProfileRepository
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher_engine.domain.listing import Listing
from rentczecher_engine.domain.location import ParsedPlace, PlaceKind, PlaceRef
from rentczecher_engine.domain.profile import Criteria, Preferences
from rentczecher_engine.services.pipeline import PipelineDeps, run_profile
from tests.profiles import layouts, preferences

SCENARIOS_DIR = Path(__file__).parent

# What a listing is unless its scenario says otherwise. A scenario spells out
# only what makes it different, so these stay plain.
DEFAULT_LISTING = {
    "title": "Pronájem bytu 2+kk 50 m²",
    "location_raw_text": "Praha 7",
    "size_m2": 50,
    "disposition_raw_text": "2+kk",
}

_SEARCH_KEYS = {"offer_type", "estate_type", "place", "min_price", "max_price",
                "min_size_m2", "max_size_m2", "min_land_m2", "dispositions"}
_PREFERENCE_KEYS = {"price_per_m2_weight", "disposition_weight", "preferred_dispositions",
                    "size_weight", "preferred_size_m2", "place_weight", "preferred_places",
                    "land_weight", "preferred_land_m2", "price_weight", "preferred_price"}

# The user config's format, which the panel checks on reading it.
USER_CONFIG_VERSION = 1
_THEMES = ("system", "light", "dark")
_LANGUAGES = ("cs", "en")
FIRST_RUN = "first-run"

_OFFSET = re.compile(r"^-(\d+)([dhm])$")
_OFFSET_UNITS = {"d": "days", "h": "hours", "m": "minutes"}


def offset_from_now(text: str) -> timedelta:
    """'-3d', '-2h' or '-30m', how long before the replay's now an event
    happened. 'now' is zero."""
    if text == "now":
        return timedelta(0)
    match = _OFFSET.match(text)
    if match is None:
        raise ValueError(f"expected 'now' or an offset like -3d, -2h, -30m, got {text!r}")
    amount, unit = match.groups()
    return -timedelta(**{_OFFSET_UNITS[unit]: int(amount)})


@dataclass(frozen=True, slots=True)
class ScenarioUserConfig:
    """The panel's user config the app starts with."""

    theme: str
    language: str


@dataclass(frozen=True, slots=True)
class ScenarioScan:
    at: timedelta
    listings: tuple[dict, ...]


class ReplayClock:
    """The time every engine write sees during a replay, moved forward by
    the replay itself rather than by the wall clock."""

    def __init__(self, now: datetime):
        self.current = now

    def __call__(self) -> datetime:
        return self.current


class ScenarioScraper:
    """Returns one portal's share of one scan's listings, in place of the
    real scraper for that portal."""

    def __init__(self, listings: list[Listing]):
        self._listings = listings

    def scrape(self) -> list[Listing]:
        return self._listings


class Scenario:
    """One scenario file: a profile, the scans it went through, the listings
    the user viewed afterwards, and the user config, None for a first run. A
    scenario without a profile is an app nobody has set up yet."""

    def __init__(self, name: str, profile: dict | None, scans: tuple[ScenarioScan, ...],
                 viewed: tuple[str, ...], user_config: ScenarioUserConfig | None):
        self.name = name
        self.profile = profile
        self.scans = scans
        self.viewed = viewed
        self.user_config = user_config

    @classmethod
    def names(cls) -> list[str]:
        return sorted(path.stem for path in SCENARIOS_DIR.glob("*.yaml"))

    @classmethod
    def load(cls, name: str) -> "Scenario":
        path = SCENARIOS_DIR / f"{name}.yaml"
        if not path.is_file():
            raise ValueError(f"no scenario {name!r}, known: {cls.names()}")
        return cls.from_text(name, path.read_text(encoding="utf-8"))

    @classmethod
    def from_text(cls, name: str, text: str) -> "Scenario":
        raw = yaml.safe_load(text)
        unknown = set(raw) - {"profile", "scans", "viewed", "panel"}
        if unknown:
            raise ValueError(f"scenario {name!r}: unknown keys {sorted(unknown)}")
        profile = raw.get("profile")
        if profile is None and ("scans" in raw or "viewed" in raw):
            raise ValueError(f"scenario {name!r}: scans and views need a profile")
        if profile is not None:
            unknown_profile = set(profile) - {"name", "search", "portals", "preferences"}
            if unknown_profile:
                raise ValueError(f"scenario {name!r}: unknown profile keys {sorted(unknown_profile)}")
        scans = tuple(
            ScenarioScan(at=offset_from_now(scan["at"]), listings=tuple(scan.get("listings") or ()))
            for scan in raw.get("scans", ())
        )
        user_config = _user_config(name, raw.get("panel", {}))
        return cls(name, profile, scans, tuple(raw.get("viewed", ())), user_config)

    def portals(self, profile: dict) -> list[str]:
        """The portals the profile states, or else every portal any scan saw
        a listing from."""
        if "portals" in profile:
            return sorted(profile["portals"])
        return self._sources()

    def _sources(self) -> list[str]:
        """Every portal any scan saw a listing from, so each scan runs them
        all and a listing one portal stops returning counts as missed."""
        sources = {_source_of(listing["id"]) for scan in self.scans for listing in scan.listings}
        return sorted(sources)

    def replay_into(self, home: Path, now: datetime) -> str | None:
        """Adds the scenario's profile, dated at its first scan, to a fresh
        home/data/rentczecher.db, replays every scan, then every view, writes
        the user config, and returns the profile's id, None without a profile.
        A home that already holds a database is refused, since replaying on
        top would stack two stories."""
        if (home / "data" / "rentczecher.db").exists():
            raise ValueError(f"{home} already holds a database, replay into a fresh folder")
        data_dir = home / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._write_user_config(home)

        conn = connection.connect(data_dir / "rentczecher.db")
        try:
            migrate.apply_pending(conn)
            conn.commit()
            if self.profile is None:
                return None
            return self._replay_profile(conn, self.profile, now)
        finally:
            conn.close()

    def _write_user_config(self, home: Path) -> None:
        if self.user_config is None:
            return
        contents = {
            "version": USER_CONFIG_VERSION,
            "theme": self.user_config.theme,
            "language": self.user_config.language,
        }
        (home / "user_config.json").write_text(json.dumps(contents, indent=2) + "\n", encoding="utf-8")

    def _replay_profile(self, conn: sqlite3.Connection, stated: dict, now: datetime) -> str:
        clock = ReplayClock(now)
        store = SqliteRunStore(conn, now=clock)
        gazetteer = Gazetteer()
        if self.scans:
            clock.current = now + self.scans[0].at
        profile = SqliteProfileRepository(conn, now=clock).add(
            stated["name"], tuple(self.portals(stated)), self._criteria(stated, gazetteer),
            self._preferences(stated, gazetteer))
        conn.commit()
        for scan in self.scans:
            clock.current = now + scan.at
            deps = PipelineDeps(
                store=store,
                clock=clock,
                client=None,
                scrapers=self._scrapers_for(scan, clock.current),
                gazetteer=gazetteer,
            )
            run_profile(profile, deps)
        clock.current = now
        for listing_id in self.viewed:
            (property_id,) = conn.execute(
                "SELECT property_id FROM listings WHERE id = ?", (listing_id,)).fetchone()
            store.mark_viewed(profile.id, property_id)
        return profile.id

    def _criteria(self, profile: dict, gazetteer: Gazetteer) -> Criteria:
        """The profile's search, its place written by kind and name, like
        'obvod Praha 7'. An unknown key or place kind, or a place name that
        is unknown or ambiguous, fails loudly."""
        search = profile["search"]
        unknown = set(search) - _SEARCH_KEYS
        if unknown:
            raise ValueError(f"scenario {self.name!r}: unknown search keys {sorted(unknown)}")
        return Criteria(
            offer_type=search["offer_type"],
            estate_type=search["estate_type"],
            place=self._place(gazetteer, search["place"]),
            min_price=search.get("min_price"),
            max_price=search.get("max_price"),
            min_size_m2=search.get("min_size_m2"),
            max_size_m2=search.get("max_size_m2"),
            min_land_m2=search.get("min_land_m2"),
            dispositions=layouts(*search.get("dispositions", [])),
        )

    def _preferences(self, profile: dict, gazetteer: Gazetteer) -> Preferences:
        """The profile's preferences, every one off unless the scenario sets
        it, with preferred places written like the search place."""
        stated = profile.get("preferences", {})
        unknown = set(stated) - _PREFERENCE_KEYS
        if unknown:
            raise ValueError(f"scenario {self.name!r}: unknown preference keys {sorted(unknown)}")
        return preferences(
            price_per_m2_weight=stated.get("price_per_m2_weight", 0),
            disposition_weight=stated.get("disposition_weight", 0),
            preferred_dispositions=layouts(*stated.get("preferred_dispositions", [])),
            size_weight=stated.get("size_weight", 0),
            preferred_size_m2=stated.get("preferred_size_m2"),
            place_weight=stated.get("place_weight", 0),
            preferred_places=tuple(self._place(gazetteer, written) for written in stated.get("preferred_places", [])),
            land_weight=stated.get("land_weight", 0),
            preferred_land_m2=stated.get("preferred_land_m2"),
            price_weight=stated.get("price_weight", 0),
            preferred_price=stated.get("preferred_price"),
        )

    def _place(self, gazetteer: Gazetteer, written: str) -> PlaceRef:
        kind, _, place_name = written.partition(" ")
        place_kinds = get_args(PlaceKind)
        if kind not in place_kinds:
            raise ValueError(
                f"scenario {self.name!r}: unknown place kind {kind!r}, expected one of {list(place_kinds)}")
        return gazetteer.place_named(kind, place_name)

    def _scrapers_for(self, scan: ScenarioScan, scraped_at: datetime) -> dict[str, Callable[[Criteria, object], ScenarioScraper]]:
        by_portal: dict[str, list[Listing]] = {portal: [] for portal in self._sources()}
        for fields in scan.listings:
            listing = _build_listing(fields, scraped_at)
            by_portal[listing.source].append(listing)
        return {
            portal: _scraper_returning(listings)
            for portal, listings in by_portal.items()
        }


def _user_config(name: str, stated: dict | str) -> ScenarioUserConfig | None:
    """The user config a scenario states, the defaults where it states
    nothing, or None for a first run. An unknown key or value fails loudly."""
    if stated == FIRST_RUN:
        return None
    if not isinstance(stated, dict):
        raise ValueError(f"scenario {name!r}: panel must be {FIRST_RUN!r} or a mapping, got {stated!r}")
    unknown = set(stated) - {"theme", "language"}
    if unknown:
        raise ValueError(f"scenario {name!r}: unknown panel keys {sorted(unknown)}")
    user_config = ScenarioUserConfig(theme=stated.get("theme", "system"), language=stated.get("language", "cs"))
    if user_config.theme not in _THEMES:
        raise ValueError(f"scenario {name!r}: theme must be one of {list(_THEMES)}, got {user_config.theme!r}")
    if user_config.language not in _LANGUAGES:
        raise ValueError(
            f"scenario {name!r}: language must be one of {list(_LANGUAGES)}, got {user_config.language!r}")
    return user_config


def _scraper_returning(listings: list[Listing]) -> Callable[[Criteria, object], ScenarioScraper]:
    def make(criteria: Criteria, client: object) -> ScenarioScraper:
        return ScenarioScraper(listings)
    return make


def _source_of(listing_id: str) -> str:
    source, separator, _ = listing_id.partition(":")
    if not separator:
        raise ValueError(f"listing id {listing_id!r} must be portal:id, like sreality:123")
    return source


def _build_listing(fields: dict, scraped_at: datetime) -> Listing:
    """A listing from its scenario fields over the defaults. Unknown fields
    fail loudly, through the engine's own Listing.build."""
    merged = {**DEFAULT_LISTING, **fields}
    derived = {
        "source": _source_of(merged["id"]),
        "url": f"https://example.invalid/{merged['id']}",
        "scraped_at": scraped_at.isoformat(),
        "parsed_place": ParsedPlace(names=tuple(part.strip() for part in merged["location_raw_text"].split(","))),
    }
    return Listing.build(**{**derived, **merged})
