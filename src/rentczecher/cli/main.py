#!/usr/bin/env python3
"""Byt Watchdog - Multi-profile real estate monitor."""

import argparse
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from rentczecher.adapters.config import paths
from rentczecher.adapters.config.loader import load_config
from rentczecher.adapters.geocoding.gazetteer import Gazetteer
from rentczecher.adapters.notifiers.smtp import SmtpNotifier
from rentczecher.adapters.repositories.sqlite import connection, migrate
from rentczecher.adapters.repositories.sqlite.clock import utc_now
from rentczecher.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher.adapters.scrapers import ALL_SCRAPERS
from rentczecher.adapters.scrapers.client import build_client
from rentczecher.domain.errors import ConfigError, ConfigNotFoundError
from rentczecher.domain.search import SearchSpec
from rentczecher.services.notify import Notification
from rentczecher.services.pipeline import PipelineDeps, ProfileRunResult, run_profile
from rentczecher.services.scrape import Scraper

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


def _build_smtp_notifier(email_cfg: dict, profile_id: str, recipients: list[str]) -> SmtpNotifier | None:
    if not recipients:
        return None
    return SmtpNotifier(
        smtp_host=email_cfg["smtp_host"],
        smtp_port=email_cfg["smtp_port"],
        smtp_user=email_cfg["smtp_user"],
        smtp_password=email_cfg["smtp_password"],
        from_address=email_cfg["from"],
        recipients=tuple(recipients),
    )


class _NoRecipientsNotifier:
    """Stands in for a profile with no configured recipients: a run still
    persists its outcome, it just never sends anything. The warning only
    fires when there was actually something to notify about."""

    def __init__(self, profile_id: str):
        self._profile_id = profile_id

    def send(self, notification: Notification) -> bool:
        log.error("Profile %s has no 'to' recipients configured - skipping email", self._profile_id)
        return True


def _log_run_result(profile_id: str, result: ProfileRunResult) -> None:
    for name, health in sorted(result.scraper_health.items()):
        if health.status == "broken":
            log.warning("  %s: broken (%s)", name, health.error or "unknown error")
        elif health.status == "zero_results":
            log.warning("  %s: 0 results", name)
        else:
            log.info("  %s: %d listing(s)", name, health.listing_count)

    if result.status == "failed":
        log.error("Profile %s failed: %s", profile_id, result.error or "check search.place")
        return

    counts = result.counts
    log.info("Profile %s [%s]: %d listings, %d new, %d price drops, %d disappeared",
             profile_id, result.status, counts.total, counts.new,
             counts.price_drops, counts.disappeared)


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

                log.info("=== Profile: %s ===", profile.get("name", profile_id))
                if dry_run:
                    log.info("DRY RUN - no emails, no DB updates")

                if not profile["scrapers"]:
                    log.warning("Profile %s has no enabled scrapers", profile_id)
                    continue

                # PipelineDeps.scrapers is typed against a bare `object` client
                # (services/ cannot name httpx.Client), so each concrete
                # scraper constructor is widened here at the adapter boundary.
                scrapers = {
                    name: cast(Callable[[SearchSpec, object], Scraper], cls)
                    for name, cls in ALL_SCRAPERS.items() if name in profile["scrapers"]
                }
                notifier = _build_smtp_notifier(
                    email_cfg, profile_id, profile.get("to", [])) or _NoRecipientsNotifier(profile_id)
                deps = PipelineDeps(
                    store=store,
                    clock=utc_now,
                    client=client,
                    scrapers=scrapers,
                    gazetteer=gazetteer,
                    notifier=notifier,
                )
                try:
                    result = run_profile({**profile, "id": profile_id}, deps, dry_run=dry_run)
                except Exception:
                    log.exception("Profile %s failed", profile_id)
                    continue
                _log_run_result(profile_id, result)
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
