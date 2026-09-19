#!/usr/bin/env python3
"""Byt Watchdog - Multi-profile real estate monitor."""

import argparse
import logging
import os
import sys
from pathlib import Path

import httpx

from rentczecher.adapters.config import paths
from rentczecher.adapters.config.loader import load_config
from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher.domain.errors import ConfigError, ConfigNotFoundError, PlaceNotFoundError
from rentczecher.domain.search import SearchSpec
from rentczecher.services.dedup import cross_source_dedup
from rentczecher.services.diff import classify
from rentczecher.services.locate import locate_listings
from rentczecher.adapters.enrichment.metro import enrich_tram
from rentczecher.adapters.notifiers.smtp import send_email
from rentczecher.services.scrape import scrape_all
from rentczecher.services.score import compute_score
from rentczecher.adapters.scrapers import ALL_SCRAPERS
from rentczecher.adapters.scrapers.client import build_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("rentczecher")

CONFIG_PATH = str(paths.config_path())
PID_PATH = str(paths.pid_lock_path())


def _load_config_or_exit() -> dict:
    try:
        return load_config(Path(CONFIG_PATH))
    except ConfigNotFoundError as error:
        log.error("%s - run ./install.py, or copy config.example.yaml "
                  "there and fill in your settings.", error)
        sys.exit(1)
    except ConfigError as error:
        log.error("Invalid config:\n%s", error)
        sys.exit(1)


def validate_config(path: Path | None = None) -> int:
    config_file = path if path is not None else Path(CONFIG_PATH)
    try:
        config = load_config(config_file)
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    profiles = config["profiles"]
    enabled = sum(len(profile["scrapers"]) for profile in profiles.values())
    print(f"OK - {len(profiles)} profile(s), {enabled} scraper(s) enabled")
    return 0


def migrate_db() -> int:
    db_file = paths.db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = connection.connect(db_file)
    try:
        applied = migrate.apply_pending(conn)
    finally:
        conn.close()
    if applied:
        print(f"Applied migration(s) {', '.join(map(str, applied))} to {db_file}")
    else:
        print(f"OK - schema up to date at {db_file}")
    return 0


def _acquire_pidlock() -> bool:
    os.makedirs(os.path.dirname(PID_PATH), exist_ok=True)
    if os.path.exists(PID_PATH):
        try:
            with open(PID_PATH, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            return False
        except (ValueError, OSError):
            pass  # Stale/corrupt pidfile, safe to reclaim
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))
    return True


def _release_pidlock():
    try:
        os.unlink(PID_PATH)
    except OSError:
        pass


def _apply_filters(listings: list, spec: SearchSpec) -> list:
    result = listings
    if spec.dispositions:
        disp_lower = {d.lower() for d in spec.dispositions}
        result = [
            l for l in result
            if l.disposition is None or l.disposition.lower() in disp_lower
        ]

    if spec.min_size_m2 > 0:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= spec.min_size_m2]

    if spec.min_land_m2 > 0:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= spec.min_land_m2]

    return result


def run_profile(profile_id: str, profile: dict, email_cfg: dict,
                client: httpx.Client, store: SqliteRunStore,
                dry_run: bool = False,
                gazetteer: Gazetteer | None = None):
    """Run a single profile: scrape, filter, score, notify."""
    profile_name = profile.get("name", profile_id)
    log.info("=== Profile: %s ===", profile_name)

    spec = SearchSpec.from_search_config(profile["search"])

    # Scrape all sources for this profile
    enabled_scrapers = profile.get("scrapers", [])
    if not enabled_scrapers:
        log.warning("Profile %s has no enabled scrapers", profile_id)
        return

    scraper_classes = {name: cls for name, cls in ALL_SCRAPERS.items() if name in enabled_scrapers}
    try:
        all_listings, _scraper_health = scrape_all(scraper_classes, spec, client)
    except PlaceNotFoundError as error:
        log.error("Profile %s: %s - fix search.place", profile_id, error)
        return

    if not all_listings:
        log.info("No listings found for profile %s", profile_id)
        return

    # Apply filters
    filtered = _apply_filters(all_listings, spec)
    if len(filtered) < len(all_listings):
        log.info("Filtered: %d -> %d listings", len(all_listings), len(filtered))
    all_listings = filtered

    # Enrich with tram distances (only for Prague profiles)
    if profile.get("tram_enrichment", False):
        all_listings = [enrich_tram(listing) for listing in all_listings]

    # Locate listings
    if gazetteer is None:
        gazetteer = Gazetteer()
    all_listings = locate_listings(all_listings, gazetteer)

    # Cross-source dedup
    pre_dedup = len(all_listings)
    located_by_id = {l.id: l for l in all_listings}
    outcome = cross_source_dedup(all_listings, gazetteer)
    all_listings = outcome.survivors
    if pre_dedup > len(all_listings):
        log.info("Cross-source dedup: %d -> %d listings", pre_dedup, len(all_listings))

    # Compute scores
    all_listings = [l.with_annotations(score=compute_score(l, profile)) for l in all_listings]

    seen = store.seen_ids(profile_id)
    latest_prices = store.latest_prices(profile_id)

    # Detect disappeared (requires 3+ consecutive misses to filter API noise).
    # Computed read-only: the miss-count increment itself lands only with the
    # rest of persist_outcome, after a successful send.
    # An absorbed listing was present in this scrape, so it counts toward
    # the miss reset even though it never survives dedup.
    current_ids = {l.id for l in all_listings} | {m.absorbed_id for m in outcome.merges}
    disappeared = store.pending_disappeared(profile_id, current_ids)
    if disappeared:
        log.info("Disappeared: %d listings confirmed gone (3+ misses)", len(disappeared))

    diff = classify(all_listings, seen, latest_prices, disappeared)
    new_listings = diff.new
    price_drop_listings = diff.price_drops
    for listing in price_drop_listings:
        log.info("  PRICE DROP: %s | %d -> %d Kc", listing.title[:50], listing.price_drop_from, listing.price)

    notable = new_listings + price_drop_listings
    log.info("Total: %d listings, %d new, %d price drops, %d disappeared",
             len(all_listings), len(new_listings), len(price_drop_listings), len(disappeared))

    if not notable:
        if not dry_run:
            store.persist_outcome(profile_id, profile_name, outcome, located_by_id, current_ids)
        if disappeared:
            log.info("Only disappeared listings (%d) - no email sent", len(disappeared))
        else:
            log.info("No new listings or changes to report")
        return

    if dry_run:
        for l in new_listings:
            extra = f" | land={l.land_m2}m2" if l.land_m2 else ""
            log.info("  [NEW] score=%d | %s | %d Kc | %s%s | %s",
                     l.score, l.disposition or "?", l.price, l.location, extra, l.url)
        for l in price_drop_listings:
            log.info("  [DROP] %d -> %d Kc | %s", l.price_drop_from, l.price, l.title[:50])
        for d in disappeared[:5]:
            log.info("  [GONE] %s | %d Kc", (d.title or "?")[:50], d.price or 0)
        log.info("DRY RUN complete for %s", profile_id)
        return

    # Determine recipients - profile-level "to" overrides global
    recipients = profile.get("to", [])

    if not recipients:
        log.error("Profile %s has no 'to' recipients configured - skipping email", profile_id)
        store.persist_outcome(profile_id, profile_name, outcome, located_by_id, current_ids)
        return

    # Send email FIRST
    try:
        merged_email_cfg = {**email_cfg, "to": recipients}
        send_email(notable, merged_email_cfg, spec, profile=profile, disappeared=disappeared)
        log.info("Email sent to %s with %d new + %d price drops",
                 ", ".join(recipients), len(new_listings), len(price_drop_listings))
    except Exception:
        log.exception("Failed to send email for %s - will retry next run", profile_id)
        return

    # Persist AFTER successful email
    store.persist_outcome(profile_id, profile_name, outcome, located_by_id, current_ids)
    store.prune(profile_id)


def _warn_if_repo_data_orphaned():
    repo_data = paths.repo_root() / "data"
    if repo_data == paths.data_dir() or os.environ.get("RENTCZECHER_DATA_DIR"):
        return
    if any(repo_data.glob("seen-*.json")):
        log.warning(
            "Repo-local seen-*.json files at %s are not in use. "
            "Runs now store data in %s.",
            repo_data, paths.data_dir(),
        )


def run(dry_run: bool = False, profile_filter: str | None = None):
    log.info("Using config: %s, data: %s", CONFIG_PATH, paths.data_dir())
    _warn_if_repo_data_orphaned()
    config = _load_config_or_exit()

    db_file = paths.db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = connection.connect(db_file)
    if not _acquire_pidlock():
        conn.close()
        log.warning("Another instance is already running, exiting")
        return
    try:
        migrate.apply_pending(conn)
        store = SqliteRunStore(conn)

        email_cfg = config.get("email", {})
        profiles = config.get("profiles", {})

        if not profiles:
            log.error("No profiles defined in config.yaml")
            return

        gazetteer = Gazetteer()
        with build_client() as client:
            for profile_id, profile in profiles.items():
                if profile_filter and profile_id != profile_filter:
                    continue
                if not profile.get("enabled", True):
                    log.info("Profile %s is disabled, skipping", profile_id)
                    continue

                if dry_run:
                    log.info("DRY RUN - no emails, no DB updates")

                try:
                    run_profile(profile_id, profile, email_cfg, client, store,
                                dry_run, gazetteer)
                except Exception:
                    log.exception("Profile %s failed", profile_id)
    finally:
        conn.close()
        _release_pidlock()


def main():
    parser = argparse.ArgumentParser(description="Byt Watchdog - Real estate monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape and show results without sending email or updating DB")
    parser.add_argument("--profile", type=str, default=None,
                        help="Run only a specific profile (by ID)")
    subparsers = parser.add_subparsers(dest="command")
    config_parser = subparsers.add_parser("config", help="Configuration utilities")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    validate_parser = config_subparsers.add_parser("validate", help="Validate the config file")
    validate_parser.add_argument("--path", type=Path, default=None,
                                 help="Config file to validate (default: the resolved config)")
    db_parser = subparsers.add_parser("db", help="Database utilities")
    db_subparsers = db_parser.add_subparsers(dest="db_command")
    db_subparsers.add_parser("migrate", help="Create or upgrade the database schema")
    args = parser.parse_args()

    if args.command == "config":
        if args.config_command == "validate":
            sys.exit(validate_config(args.path))
        config_parser.error("expected a subcommand: validate")
    if args.command == "db":
        if args.db_command == "migrate":
            sys.exit(migrate_db())
        db_parser.error("expected a subcommand: migrate")
    run(dry_run=args.dry_run, profile_filter=args.profile)


if __name__ == "__main__":
    main()
