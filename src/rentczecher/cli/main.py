#!/usr/bin/env python3
"""Byt Watchdog - Multi-profile real estate monitor."""

import argparse
import logging
import os
import sys
from pathlib import Path

import httpx

from rentczecher.adapters import legacy_json_db as db
from rentczecher.adapters.config import paths
from rentczecher.adapters.config.loader import load_config as load_validated_config
from rentczecher.domain.errors import ConfigError
from rentczecher.services.dedup import cross_source_dedup
from rentczecher.adapters.enrichment.metro import enrich_tram
from rentczecher.adapters.notifiers.smtp import send_email
from rentczecher.services.score import compute_score
from rentczecher.adapters.scrapers import ALL_SCRAPERS
from rentczecher.adapters.scrapers.base import ScraperBrokenError
from rentczecher.adapters.scrapers.client import build_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("rentczecher")

CONFIG_PATH = str(paths.config_path())
PID_PATH = str(paths.pid_lock_path())


def load_config() -> dict:
    config_file = Path(CONFIG_PATH)
    if not config_file.exists():
        log.error("Config not found at %s - run ./install.py, or copy "
                  "config.example.yaml there and fill in your settings.", CONFIG_PATH)
        sys.exit(1)
    try:
        return load_validated_config(config_file)
    except ConfigError as error:
        log.error("Invalid config:\n%s", error)
        sys.exit(1)


def validate_config(path: Path | None = None) -> int:
    config_file = path if path is not None else Path(CONFIG_PATH)
    if not config_file.exists():
        print(f"error: config not found at {config_file}", file=sys.stderr)
        return 1
    try:
        config = load_validated_config(config_file)
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    profiles = config["profiles"]
    enabled = sum(
        1 for profile in profiles.values()
        for scraper in profile["scrapers"].values() if scraper["enabled"]
    )
    print(f"OK - {len(profiles)} profile(s), {enabled} scraper(s) enabled")
    for profile_id, profile in profiles.items():
        if profile["scrapers"].get("remax", {}).get("search_url"):
            print(f"WARNING: profiles.{profile_id}.scrapers.remax.search_url is "
                  "deprecated; it will be replaced by resolver-based location "
                  "parameters and later become an error")
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


def _apply_filters(listings: list, profile: dict) -> list:
    search = profile.get("search", {})
    dispositions = search.get("dispositions", [])
    min_size = search.get("min_size_m2", 0)
    min_land = search.get("min_land_m2", 0)

    result = listings
    if dispositions:
        disp_lower = {d.lower() for d in dispositions}
        result = [
            l for l in result
            if l.disposition is None or l.disposition.lower() in disp_lower
        ]

    if min_size > 0:
        result = [l for l in result if l.size_m2 is None or l.size_m2 >= min_size]

    if min_land > 0:
        result = [l for l in result if l.land_m2 is None or l.land_m2 >= min_land]

    return result


def run_profile(profile_id: str, profile: dict, email_cfg: dict,
                client: httpx.Client, dry_run: bool = False):
    """Run a single profile: scrape, filter, score, notify."""
    profile_name = profile.get("name", profile_id)
    log.info("=== Profile: %s ===", profile_name)

    # Scrape all sources for this profile
    all_listings = []
    scraper_configs = profile.get("scrapers", {})
    enabled_count = sum(1 for n in ALL_SCRAPERS if scraper_configs.get(n, {}).get("enabled", False))
    if enabled_count == 0:
        log.warning("Profile %s has no enabled scrapers", profile_id)
        return

    for name, scraper_cls in ALL_SCRAPERS.items():
        scraper_cfg = scraper_configs.get(name, {})
        if not scraper_cfg.get("enabled", False):
            continue

        log.info("Running scraper: %s", name)
        try:
            scraper = scraper_cls(profile, client)
            listings = scraper.scrape()
            if len(listings) == 0:
                log.warning("  %s: returned 0 results - site structure may have changed!", name)
            else:
                log.info("  %s: found %d listings", name, len(listings))
            all_listings.extend(listings)
        except ScraperBrokenError as error:
            log.error("  %s: portal changed its contract - scraper needs updating: %s", name, error)
        except Exception:
            log.exception("  %s: scraper failed", name)

    if not all_listings:
        log.info("No listings found for profile %s", profile_id)
        return

    # Apply filters
    filtered = _apply_filters(all_listings, profile)
    if len(filtered) < len(all_listings):
        log.info("Filtered: %d -> %d listings", len(all_listings), len(filtered))
    all_listings = filtered

    # Enrich with tram distances (only for Prague profiles)
    if profile.get("tram_enrichment", False):
        all_listings = [enrich_tram(listing) for listing in all_listings]

    # Cross-source dedup
    pre_dedup = len(all_listings)
    all_listings = cross_source_dedup(all_listings)
    if pre_dedup > len(all_listings):
        log.info("Cross-source dedup: %d -> %d listings", pre_dedup, len(all_listings))

    # Compute scores
    all_listings = [l.with_annotations(score=compute_score(l, profile)) for l in all_listings]

    # Check for price drops; all_listings is the single source of truth, so
    # the annotated replacements land there and everything below derives
    # from it.
    price_drops = db.update_prices(profile_id, all_listings)
    dropped = {}
    for listing, old_price in price_drops:
        dropped[listing.id] = listing.with_annotations(price_drop_from=old_price)
        log.info("  PRICE DROP: %s | %d -> %d Kc", listing.title[:50], old_price, listing.price)
    all_listings = [dropped.get(l.id, l) for l in all_listings]

    # Find new listings BEFORE updating DB
    seen = db.get_seen(profile_id)
    new_listings = [l for l in all_listings if l.id not in seen]
    new_ids = {n.id for n in new_listings}
    price_drop_listings = [
        l for l in all_listings
        if l.price_drop_from is not None and l.id not in new_ids
    ]

    # Detect disappeared (requires 3+ consecutive misses to filter API noise).
    # Dry-run skips the write, so it previews disappearances from the last
    # real run's counters.
    current_ids = {l.id for l in all_listings}
    if not dry_run:
        db.update_miss_counts(profile_id, current_ids)
    disappeared = db.get_disappeared(profile_id, current_ids)
    if disappeared:
        log.info("Disappeared: %d listings confirmed gone (3+ misses)", len(disappeared))

    notable = new_listings + price_drop_listings
    log.info("Total: %d listings, %d new, %d price drops, %d disappeared",
             len(all_listings), len(new_listings), len(price_drops), len(disappeared))

    if not notable:
        if not dry_run:
            db.mark_seen(profile_id, all_listings)
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
            log.info("  [GONE] %s | %d Kc", d.get("title", "?")[:50], d.get("price", 0))
        log.info("DRY RUN complete for %s", profile_id)
        return

    # Determine recipients - profile-level "to" overrides global
    recipients = profile.get("to", [])

    if not recipients:
        log.error("Profile %s has no 'to' recipients configured - skipping email", profile_id)
        db.mark_seen(profile_id, all_listings)
        return

    # Send email FIRST
    try:
        merged_email_cfg = {**email_cfg, "to": recipients}
        send_email(notable, merged_email_cfg, profile=profile, disappeared=disappeared)
        log.info("Email sent to %s with %d new + %d price drops",
                 ", ".join(recipients), len(new_listings), len(price_drop_listings))
    except Exception:
        log.exception("Failed to send email for %s - will retry next run", profile_id)
        return

    # Mark as seen AFTER successful email
    db.mark_seen(profile_id, all_listings)
    db.prune(profile_id, max_age_days=90)


def _warn_if_repo_data_orphaned():
    repo_data = paths.repo_root() / "data"
    if str(repo_data) == db.DATA_DIR or os.environ.get("RENTCZECHER_DATA_DIR"):
        return
    if any(repo_data.glob("seen-*.json")):
        log.warning(
            "Repo-local state at %s is not in use; runs now store data in %s. "
            "Move the seen-*.json files there if that history should carry over.",
            repo_data, db.DATA_DIR,
        )


def run(dry_run: bool = False, profile_filter: str | None = None):
    log.info("Using config: %s, data: %s", CONFIG_PATH, db.DATA_DIR)
    _warn_if_repo_data_orphaned()
    config = load_config()

    if not _acquire_pidlock():
        log.warning("Another instance is already running, exiting")
        return
    try:
        email_cfg = config.get("email", {})
        profiles = config.get("profiles", {})

        if not profiles:
            log.error("No profiles defined in config.yaml")
            return

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
                    run_profile(profile_id, profile, email_cfg, client, dry_run)
                except Exception:
                    log.exception("Profile %s failed", profile_id)
    finally:
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
    args = parser.parse_args()

    if args.command == "config":
        if args.config_command == "validate":
            sys.exit(validate_config(args.path))
        config_parser.error("expected a subcommand: validate")
    run(dry_run=args.dry_run, profile_filter=args.profile)


if __name__ == "__main__":
    main()
