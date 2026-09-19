"""Golden test pinning the exact end-to-end pipeline behavior.

Feeds a fixed set of fixture listings through run_profile (filters,
cross-source dedup, scoring, price drops, disappearances,
notify-then-commit) and compares the full outcome against a committed
golden file. Regenerate deliberately with:
PARITY_REGEN=1 python3 -m pytest tests/test_pipeline_parity.py

Run: python3 -m pytest tests/test_pipeline_parity.py -v
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.location import ParsedPlace
from rentczecher.services.pipeline import PipelineDeps, run_profile

FIXTURES = Path(__file__).parent / "fixtures" / "parity"
GOLDEN = FIXTURES / "golden.json"

GAZETTEER = Gazetteer()

PROFILE_ID = "parity"
PROFILE = {
    "name": "Parity profile",
    "enabled": True,
    "to": ["parity@example.com"],
    "search": {
        "offer_type": "rent",
        "estate_type": "flat",
        "place": "praha-7",
        "min_price": 0,
        "max_price": 25000,
        "dispositions": ["2+kk", "1+1"],
        "min_size_m2": 30,
    },
    "scrapers": ["sreality", "bezrealitky", "remax"],
    "scoring": {
        "price_per_m2_weight": 40,
        "disposition_weight": 30,
        "preferred_dispositions": ["2+kk", "1+1"],
        "size_weight": 15,
        "ideal_size_m2": 55,
        "neighborhood_weight": 15,
        "preferred_neighborhoods": ["Holešovice", "Letná"],
    },
}
PROFILE_WITH_ID = {**PROFILE, "id": PROFILE_ID}


def _build_fixture_listing(record):
    record = dict(record)
    place = record.get("parsed_place")
    if place is not None:
        record["parsed_place"] = ParsedPlace(names=tuple(place["names"]), district=place.get("district"))
    return Listing.build(**record)


def _fake_scrapers(listing_data):
    scrapers = {}
    for source, records in listing_data.items():
        class FakeScraper:
            _records = records

            def __init__(self, spec, client):
                pass

            def scrape(self):
                return [_build_fixture_listing(r) for r in self._records]

        scrapers[source] = FakeScraper
    return scrapers


def _seed_seen_state(conn):
    """Previously-seen state: one price-drop candidate and one listing at the
    disappearance threshold."""
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn.execute(
        "INSERT INTO profiles (id, name, active, created_at) VALUES (?, ?, 1, ?)",
        (PROFILE_ID, "Parity profile", recent))
    seeded = [
        # Already seen at a higher price -> must surface as a price drop.
        ("prop-1002", "sreality:1002", "Pronájem bytu 1+1 40 m²",
         "Kamenická, Praha", 40, "1+1", 24000, 0, "https://www.sreality.cz/detail/1002"),
        # Missing for 2 runs already; this run is the third -> disappeared.
        ("prop-9999", "sreality:9999", "Pronájem bytu 1+kk 30 m²",
         "Tusarova, Praha", 30, "1+kk", 18000, 2, "https://www.sreality.cz/detail/9999"),
    ]
    for prop_id, listing_id, title, location, size_m2, disposition, price, misses, url in seeded:
        conn.execute(
            "INSERT INTO properties (id, created_at, title, location, size_m2, disposition) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (prop_id, recent, title, location, size_m2, disposition))
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES (?, ?, 'sreality', ?, ?)",
            (listing_id, prop_id, url, recent))
        conn.execute(
            "INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, "
            "last_seen_at, miss_count) VALUES (?, ?, ?, ?, ?)",
            (PROFILE_ID, listing_id, recent, recent, misses))
        conn.execute(
            "INSERT INTO price_observations (listing_id, price, observed_at) VALUES (?, ?, ?)",
            (listing_id, price, recent))
    conn.commit()


def _listing_snapshot(listing):
    return {
        "id": listing.id,
        "source": listing.source,
        "title": listing.title,
        "price": listing.price,
        "location": listing.location,
        "url": listing.url,
        "image_url": listing.image_url,
        "size_m2": listing.size_m2,
        "disposition": listing.disposition,
        "lat": listing.lat,
        "lon": listing.lon,
        "charges": listing.charges,
        "land_m2": listing.land_m2,
        "score": listing.score,
        "price_drop_from": listing.price_drop_from,
        "cross_source": sorted(listing.cross_source),
    }


def _seen_snapshot(conn):
    """Every listing the profile tracks, with its property facts and latest
    price, timestamps excluded."""
    stmt = """
        SELECT listings.id AS id, listings.source AS source, listings.url AS url,
               listing_tracking.miss_count AS miss_count,
               properties.title AS title, properties.location AS location,
               properties.size_m2 AS size_m2, properties.disposition AS disposition,
               properties.land_m2 AS land_m2,
               latest_price.price AS price
        FROM listing_tracking
        JOIN listings ON listings.id = listing_tracking.listing_id
        JOIN properties ON properties.id = listings.property_id
        LEFT JOIN price_observations AS latest_price
            ON latest_price.id = (
                SELECT id FROM price_observations
                WHERE listing_id = listings.id
                ORDER BY observed_at DESC, id DESC
                LIMIT 1
            )
        ORDER BY listings.id
    """
    return {
        row["id"]: {
            "source": row["source"], "url": row["url"],
            "miss_count": row["miss_count"], "price": row["price"],
            "title": row["title"], "location": row["location"],
            "size_m2": row["size_m2"], "disposition": row["disposition"],
            "land_m2": row["land_m2"],
        }
        for row in conn.execute(stmt)
    }


class _CaptureNotifier:
    def __init__(self):
        self.notification = None

    def send(self, notification) -> bool:
        self.notification = notification
        return True


class _SilentNotifier:
    def send(self, notification) -> bool:
        return True


def _deps(store, scrapers, notifier):
    return PipelineDeps(
        store=store, clock=utc_now, client=None, scrapers=scrapers,
        gazetteer=GAZETTEER, notifier=notifier,
    )


def test_parity_profile_satisfies_the_config_schema():
    """The golden fixture's profile must stay a valid real-world config."""
    from rentczecher.adapters.config.schema import ProfileConfig
    ProfileConfig.model_validate(PROFILE)


def test_pipeline_outcome_matches_golden(run_store):
    store, conn = run_store
    listing_data = json.loads((FIXTURES / "listings.json").read_text())
    _seed_seen_state(conn)

    notifier = _CaptureNotifier()
    deps = _deps(store, _fake_scrapers(listing_data), notifier)
    run_profile(PROFILE_WITH_ID, deps, dry_run=False)

    notification = notifier.notification
    snapshot = {
        "notable": [_listing_snapshot(l) for l in notification.listings],
        "disappeared_ids": sorted(d.id for d in notification.disappeared),
        "seen_after": _seen_snapshot(conn),
    }

    if os.environ.get("PARITY_REGEN"):
        GOLDEN.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n")

    golden = json.loads(GOLDEN.read_text())
    assert snapshot == golden


def test_run_profile_persists_only_through_the_store(run_store):
    """A pipeline run persists through the store it is handed and writes
    no files of its own."""
    from rentczecher.adapters.config import paths

    store, _conn = run_store
    listing_data = json.loads((FIXTURES / "listings.json").read_text())

    deps = _deps(store, _fake_scrapers(listing_data), _SilentNotifier())
    run_profile(PROFILE_WITH_ID, deps, dry_run=False)

    assert store.seen_ids(PROFILE_ID)
    assert not list(paths.data_dir().glob("seen-*.json"))
