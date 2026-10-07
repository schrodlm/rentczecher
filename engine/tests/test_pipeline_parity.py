"""Golden test pinning the exact end-to-end pipeline behavior.

Feeds a fixed set of fixture listings through run_profile (filters,
cross-source dedup, price drops, disappearances, commit)
and compares the full outcome against a committed
golden file. Regenerate deliberately with:
PARITY_REGEN=1 python3 -m pytest tests/test_pipeline_parity.py

Run: python3 -m pytest tests/test_pipeline_parity.py -v
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.adapters.scrapers.base import Listing
from rentczecher_engine.domain.location import ParsedPlace
from rentczecher_engine.domain.profile import Profile
from rentczecher_engine.services import pipeline
from rentczecher_engine.services.pipeline import PipelineDeps, run_profile
from tests.profiles import criteria, layouts, stored_profile

FIXTURES = Path(__file__).parent / "fixtures" / "parity"
GOLDEN = FIXTURES / "golden.json"

GAZETTEER = Gazetteer()


def _stored_parity_profile(conn) -> Profile:
    return stored_profile(
        conn,
        name="Parity profile",
        portals=("sreality", "bezrealitky", "remax"),
        criteria=criteria(
            max_price=25000,
            dispositions=layouts("1+kk", "1+1", "2+kk", "2+1"),
            min_size_m2=30,
        ),
    )


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

            def __init__(self, criteria, client):
                pass

            def scrape(self):
                return [_build_fixture_listing(r) for r in self._records]

        scrapers[source] = FakeScraper
    return scrapers


def _seed_seen_state(conn, profile_id):
    """Previously-seen state: one price-drop candidate and one listing at the
    disappearance threshold."""
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
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
            "INSERT INTO properties (id, created_at, title, location_raw_text, size_m2, disposition_raw_text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (prop_id, recent, title, location, size_m2, disposition))
        conn.execute(
            "INSERT INTO listings (id, property_id, source, url, scraped_at) "
            "VALUES (?, ?, 'sreality', ?, ?)",
            (listing_id, prop_id, url, recent))
        conn.execute(
            "INSERT INTO listing_tracking (profile_id, listing_id, first_seen_at, "
            "last_seen_at, miss_count) VALUES (?, ?, ?, ?, ?)",
            (profile_id, listing_id, recent, recent, misses))
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
        "location_raw_text": listing.location_raw_text,
        "url": listing.url,
        "image_url": listing.image_url,
        "size_m2": listing.size_m2,
        "disposition_raw_text": listing.disposition_raw_text,
        "lat": listing.lat,
        "lon": listing.lon,
        "charges": listing.charges,
        "land_m2": listing.land_m2,
        "price_drop_from": listing.price_drop_from,
        "cross_source": sorted(listing.cross_source),
    }


def _seen_snapshot(conn):
    """Every listing the profile tracks, with its property facts and latest
    price, timestamps excluded."""
    stmt = """
        SELECT listings.id AS id, listings.source AS source, listings.url AS url,
               listing_tracking.miss_count AS miss_count,
               properties.title AS title, properties.location_raw_text AS location_raw_text,
               properties.size_m2 AS size_m2, properties.disposition_raw_text AS disposition_raw_text,
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
            "title": row["title"], "location_raw_text": row["location_raw_text"],
            "size_m2": row["size_m2"], "disposition_raw_text": row["disposition_raw_text"],
            "land_m2": row["land_m2"],
        }
        for row in conn.execute(stmt)
    }


def _deps(store, scrapers):
    return PipelineDeps(
        store=store, clock=utc_now, client=None, scrapers=scrapers,
        gazetteer=GAZETTEER,
    )


def test_pipeline_outcome_matches_golden(run_store, monkeypatch):
    store, conn = run_store
    listing_data = json.loads((FIXTURES / "listings.json").read_text())
    profile = _stored_parity_profile(conn)
    _seed_seen_state(conn, profile.id)

    captured = {}
    real_pending_disappeared = store.pending_disappeared
    real_classify = pipeline.classify

    def spying_pending_disappeared(profile_id, current_ids):
        captured["disappeared"] = real_pending_disappeared(profile_id, current_ids)
        return captured["disappeared"]

    def spying_classify(*args):
        captured["diff"] = real_classify(*args)
        return captured["diff"]

    monkeypatch.setattr(store, "pending_disappeared", spying_pending_disappeared)
    monkeypatch.setattr(pipeline, "classify", spying_classify)
    deps = _deps(store, _fake_scrapers(listing_data))
    run_profile(profile, deps, dry_run=False)

    diff = captured["diff"]
    snapshot = {
        "new": [_listing_snapshot(l) for l in diff.new],
        "price_drops": [_listing_snapshot(l) for l in diff.price_drops],
        "disappeared_ids": sorted(captured["disappeared"]),
        "seen_after": _seen_snapshot(conn),
    }

    if os.environ.get("PARITY_REGEN"):
        GOLDEN.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n")

    golden = json.loads(GOLDEN.read_text())
    assert snapshot == golden


def test_run_profile_persists_only_through_the_store(run_store):
    """A pipeline run persists through the store it is handed and writes
    no files of its own."""
    from rentczecher_engine.adapters.config import paths

    store, conn = run_store
    listing_data = json.loads((FIXTURES / "listings.json").read_text())
    profile = _stored_parity_profile(conn)

    deps = _deps(store, _fake_scrapers(listing_data))
    run_profile(profile, deps, dry_run=False)

    assert store.seen_ids(profile.id)
    assert not list(paths.data_dir().glob("seen-*.json"))
