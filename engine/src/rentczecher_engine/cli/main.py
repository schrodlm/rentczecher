#!/usr/bin/env python3
"""Byt Watchdog - Multi-profile real estate monitor."""

import argparse
import logging
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

import uvicorn

from rentczecher_engine.adapters.api.app import create_app
from rentczecher_engine.adapters.api.deps import ApiDeps
from rentczecher_engine.adapters.config import paths
from rentczecher_engine.adapters.config.loader import load_config
from rentczecher_engine.adapters.geocoding.gazetteer import Gazetteer
from rentczecher_engine.adapters.repositories.sqlite import connection, migrate
from rentczecher_engine.adapters.repositories.sqlite.clock import utc_now
from rentczecher_engine.adapters.repositories.sqlite.profiles import SqliteProfileRepository
from rentczecher_engine.adapters.repositories.sqlite.store import SqliteRunStore
from rentczecher_engine.adapters.scrapers import scraper_registry
from rentczecher_engine.adapters.scrapers.client import build_client
from rentczecher_engine.domain.errors import ConfigError
from rentczecher_engine.services.pipeline import PipelineDeps, ProfileRunResult, run_profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("rentczecher")

CONFIG_PATH = str(paths.config_path())
PID_PATH = str(paths.pid_lock_path())


def validate_config(path: Path | None = None) -> int:
    config_file = path if path is not None else Path(CONFIG_PATH)
    try:
        profiles = load_config(config_file)
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    enabled = sum(len(profile.portals) for profile in profiles)
    print(f"OK - {len(profiles)} profile(s), {enabled} scraper(s) enabled")
    return 0


def migrate_db() -> int:
    db_file = paths.db_path()
    applied = migrate.apply_pending_at(db_file)
    if applied:
        print(f"Applied migration(s) {', '.join(map(str, applied))} to {db_file}")
    else:
        print(f"OK - schema up to date at {db_file}")
    return 0


def serve(port: int, allowed_origins: list[str], exit_with_parent: bool = False) -> int:
    """Runs the sidecar API on 127.0.0.1:port. The shell spawns this exact
    subcommand, so its stdout/stderr are the only supervision signal a
    parent process has. Port 0 lets the OS pick a free port, and the port
    actually bound is announced on stdout as PORT=<n>.

    With exit_with_parent, the server shuts down once stdin reaches end of
    input. The spawner holds stdin open and never writes to it. When the
    spawner exits for any reason, crashes included, the OS closes the pipe."""
    token = os.environ.get("RENTCZECHER_API_TOKEN")
    if not token:
        log.error("RENTCZECHER_API_TOKEN must be set to run the API server")
        return 1

    db_file = paths.db_path()
    migrate.apply_pending_at(db_file)

    api_deps = ApiDeps(db_path=db_file, scrapers=scraper_registry())
    # Called from a shutdown request, long after the server below exists.
    def request_shutdown() -> None:
        server.should_exit = True

    app = create_app(token, api_deps, allowed_origins=allowed_origins,
                     request_shutdown=request_shutdown)

    # Binding before announcing makes the announced port a promise: the
    # socket already holds it, so nothing else can take it in between.
    # Open event streams never close by themselves, so a graceful shutdown
    # stops waiting for them after two seconds.
    server_config = uvicorn.Config(app, host="127.0.0.1", port=port, timeout_graceful_shutdown=2)
    sock = server_config.bind_socket()
    print(f"PORT={sock.getsockname()[1]}", flush=True)
    server = uvicorn.Server(server_config)
    if exit_with_parent:
        threading.Thread(target=_shutdown_at_end_of_stdin, args=(request_shutdown,),
                         name="parent-watch", daemon=True).start()
    server.run(sockets=[sock])
    return 0


def _shutdown_at_end_of_stdin(request_shutdown: Callable[[], None]) -> None:
    sys.stdin.buffer.read()
    request_shutdown()


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


def _log_run_result(profile_id: str, result: ProfileRunResult) -> None:
    for name, health in sorted(result.scraper_health.items()):
        if health.status == "broken":
            log.warning("  %s: broken (%s)", name, health.error or "unknown error")
        elif health.status == "zero_results":
            log.warning("  %s: 0 results", name)
        else:
            log.info("  %s: %d listing(s)", name, health.listing_count)

    if result.status == "failed":
        log.error("Profile %s failed: %s", profile_id, result.error or "check its search place")
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
    log.info("Using data: %s", paths.data_dir())
    _warn_if_repo_data_orphaned()

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
        profiles = SqliteProfileRepository(conn).list_profiles()

        if not profiles:
            log.error("No profiles in the database at %s", db_file)
            return

        gazetteer = Gazetteer()
        with build_client() as client:
            for profile in profiles:
                if profile_filter and profile.id != profile_filter:
                    continue
                if not profile.enabled:
                    log.info("Profile %s is disabled, skipping", profile.id)
                    continue

                log.info("=== Profile: %s ===", profile.name)
                if dry_run:
                    log.info("DRY RUN - no DB updates")

                if not profile.portals:
                    log.warning("Profile %s has no enabled scrapers", profile.id)
                    continue

                scrapers = scraper_registry(profile.portals)
                deps = PipelineDeps(
                    store=store,
                    clock=utc_now,
                    client=client,
                    scrapers=scrapers,
                    gazetteer=gazetteer,
                )
                try:
                    result = run_profile(profile, deps, dry_run=dry_run)
                except Exception:
                    log.exception("Profile %s failed", profile.id)
                    continue
                _log_run_result(profile.id, result)
    finally:
        conn.close()
        _release_pidlock()


def main():
    parser = argparse.ArgumentParser(description="Byt Watchdog - Real estate monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape and show results without updating DB")
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
    serve_parser = subparsers.add_parser("serve", help="Run the sidecar API server")
    serve_parser.add_argument("--port", type=int, default=8734,
                              help="Port to bind on 127.0.0.1, 0 picks a free one (default: 8734)")
    serve_parser.add_argument("--allow-origin", action="append", default=[],
                              help="Browser origin allowed to call the API (repeatable)")
    serve_parser.add_argument("--exit-with-parent", action="store_true",
                              help="Shut down when stdin closes, the spawner holds it open")
    args = parser.parse_args()

    if args.command == "config":
        if args.config_command == "validate":
            sys.exit(validate_config(args.path))
        config_parser.error("expected a subcommand: validate")
    if args.command == "db":
        if args.db_command == "migrate":
            sys.exit(migrate_db())
        db_parser.error("expected a subcommand: migrate")
    if args.command == "serve":
        sys.exit(serve(args.port, args.allow_origin, args.exit_with_parent))
    run(dry_run=args.dry_run, profile_filter=args.profile)


if __name__ == "__main__":
    main()
