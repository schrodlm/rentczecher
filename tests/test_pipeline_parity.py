"""Golden test pinning the exact end-to-end pipeline behavior.

Feeds a fixed set of fixture listings through run_profile (filters, tram
enrichment, cross-source dedup, scoring, price drops, disappearances,
notify-then-commit) and compares the full outcome against a committed
golden file. Regenerate deliberately with:
PARITY_REGEN=1 python3 -m pytest tests/test_pipeline_parity.py

Run: python3 -m pytest tests/test_pipeline_parity.py -v
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rentczecher.adapters import legacy_json_db as db
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.cli import main as main_module

FIXTURES = Path(__file__).parent / "fixtures" / "parity"
GOLDEN = FIXTURES / "golden.json"

PROFILE_ID = "parity"
PROFILE = {
    "name": "Parity profile",
    "enabled": True,
    "to": ["parity@example.com"],
    "search": {
        "offer_type": "rent",
        "estate_type": "flat",
        "min_price": 0,
        "max_price": 25000,
        "dispositions": ["2+kk", "1+1"],
        "min_size_m2": 30,
    },
    "scrapers": {
        "sreality": {"enabled": True, "locality_district_id": 5007},
        "bezrealitky": {"enabled": True},
        "remax": {"enabled": True},
    },
    "scoring": {
        "price_per_m2_weight": 40,
        "disposition_weight": 30,
        "preferred_dispositions": ["2+kk", "1+1"],
        "size_weight": 15,
        "ideal_size_m2": 55,
        "neighborhood_weight": 15,
        "preferred_neighborhoods": ["Holešovice", "Letná"],
    },
    "tram_enrichment": True,
}


def _fake_scrapers(listing_data):
    scrapers = {}
    for source, records in listing_data.items():
        class FakeScraper:
            _records = records

            def __init__(self, profile):
                pass

            def scrape(self):
                return [Listing.build(**r) for r in self._records]

        scrapers[source] = FakeScraper
    return scrapers


def _seed_seen_state(profile_id):
    """Previously-seen state: one price-drop candidate and one listing at the
    disappearance threshold."""
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    seen = {
        # Already seen at a higher price -> must surface as a price drop.
        "sreality:1002": {
            "first_seen": recent, "last_seen": recent, "price": 24000,
            "title": "Pronájem bytu 1+1 40 m²", "location": "Kamenická, Praha",
            "url": "https://www.sreality.cz/detail/1002", "source": "sreality",
            "size_m2": 40, "disposition": "1+1", "miss_count": 0,
        },
        # Missing for 2 runs already; this run is the third -> disappeared.
        "sreality:9999": {
            "first_seen": recent, "last_seen": recent, "price": 18000,
            "title": "Pronájem bytu 1+kk 30 m²", "location": "Tusarova, Praha",
            "url": "https://www.sreality.cz/detail/9999", "source": "sreality",
            "size_m2": 30, "disposition": "1+kk", "miss_count": 2,
        },
    }
    path = db._db_path(profile_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(seen, f)


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
        "nearest_stop": listing.nearest_stop,
        "stop_distance_m": listing.stop_distance_m,
        "cross_source": sorted(listing.cross_source),
    }


def _normalize_seen(seen):
    normalized = {}
    for listing_id, entry in sorted(seen.items()):
        entry = dict(entry)
        for key in ("first_seen", "last_seen"):
            if key in entry:
                entry[key] = "TS"
        normalized[listing_id] = entry
    return normalized


def test_parity_profile_satisfies_the_config_schema():
    """The golden fixture's profile must stay a valid real-world config."""
    from rentczecher.adapters.config.schema import ProfileConfig
    ProfileConfig.model_validate(PROFILE)


def test_pipeline_outcome_matches_golden(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    listing_data = json.loads((FIXTURES / "listings.json").read_text())
    monkeypatch.setattr(main_module, "ALL_SCRAPERS", _fake_scrapers(listing_data))
    _seed_seen_state(PROFILE_ID)

    sent = {}

    def capture_email(listings, email_cfg, profile=None, disappeared=None):
        sent["notable"] = listings
        sent["disappeared"] = disappeared or []

    monkeypatch.setattr(main_module, "send_email", capture_email)

    main_module.run_profile(PROFILE_ID, PROFILE, email_cfg={}, dry_run=False)

    snapshot = {
        "notable": [_listing_snapshot(l) for l in sent["notable"]],
        "disappeared_ids": sorted(d["id"] for d in sent["disappeared"]),
        "seen_after": _normalize_seen(db.get_seen(PROFILE_ID)),
    }

    if os.environ.get("PARITY_REGEN"):
        GOLDEN.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n")

    golden = json.loads(GOLDEN.read_text())
    assert snapshot == golden
