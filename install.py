#!/usr/bin/env python3
"""Installer for rentczecher: environment, config, and cron registration.

Usage: ./install.py [--no-cron] [--interval-hours N] [--dry-run]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CONFIG = REPO_ROOT / "config.yaml"
CONFIG_EXAMPLE = REPO_ROOT / "config.example.yaml"
DATA_DIR = REPO_ROOT / "data"
ENTRY_POINT = REPO_ROOT / ".venv" / "bin" / "rentczecher"
CRON_LOG = DATA_DIR / "cron.log"

CRON_BLOCK_BEGIN = "# >>> rentczecher (managed by install.py) >>>"
CRON_BLOCK_END = "# <<< rentczecher <<<"

UV_HINT = (
    "uv is required but was not found on PATH.\n"
    "Install it first: https://docs.astral.sh/uv/getting-started/installation/\n"
    "  curl -LsSf https://astral.sh/uv/install.sh | sh"
)


def step(message):
    print(f"==> {message}")


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def check_python():
    if sys.version_info < (3, 10):
        fail(f"python >= 3.10 is required, found {sys.version.split()[0]}")


def check_uv():
    if shutil.which("uv") is None:
        fail(UV_HINT)


def sync_environment(dry_run):
    step("Installing the package and its dependencies (uv sync)")
    if dry_run:
        print(f"    would run: uv sync  (in {REPO_ROOT})")
        return
    result = subprocess.run(["uv", "sync"], cwd=REPO_ROOT)
    if result.returncode != 0:
        fail("uv sync failed - see output above")


def ensure_data_dir(dry_run):
    if DATA_DIR.is_dir():
        return
    step(f"Creating data directory: {DATA_DIR}")
    if not dry_run:
        DATA_DIR.mkdir(parents=True)


def ensure_config(dry_run):
    """Create config.yaml from the example if absent; report what happened."""
    if CONFIG.exists():
        step(f"Keeping existing config: {CONFIG}")
        return "kept"
    step(f"Creating config from example: {CONFIG}")
    if not dry_run:
        shutil.copyfile(CONFIG_EXAMPLE, CONFIG)
    return "created"


def render_cron_block(interval_hours):
    # `*/24` in the hours field would only ever match hour 0 anyway; say so.
    schedule = "0 0 * * *" if interval_hours == 24 else f"0 */{interval_hours} * * *"
    entry = f"{schedule} {ENTRY_POINT} >> {CRON_LOG} 2>&1"
    return f"{CRON_BLOCK_BEGIN}\n{entry}\n{CRON_BLOCK_END}"


def strip_managed_block(crontab_text):
    lines = crontab_text.splitlines()
    kept = []
    inside = False
    for line in lines:
        if line.strip() == CRON_BLOCK_BEGIN:
            inside = True
            continue
        if line.strip() == CRON_BLOCK_END:
            inside = False
            continue
        if not inside:
            kept.append(line)
    if inside:
        # Guessing where an unterminated block ends risks deleting foreign
        # entries; refuse and make the user repair the crontab by hand.
        raise ValueError(
            "the crontab contains the rentczecher begin marker without its "
            "end marker; repair it manually (crontab -e) and re-run"
        )
    return "\n".join(kept)


def strip_legacy_entries(crontab_text):
    legacy_marker = str(REPO_ROOT / "main.py")
    kept = [line for line in crontab_text.splitlines() if legacy_marker not in line]
    return "\n".join(kept)


def merge_crontab(existing_text, interval_hours):
    """Return the new crontab: everything foreign preserved, exactly one
    managed rentczecher block, legacy pre-package entries removed."""
    cleaned = strip_managed_block(existing_text)
    cleaned = strip_legacy_entries(cleaned).strip("\n")
    block = render_cron_block(interval_hours)
    if cleaned:
        return f"{cleaned}\n\n{block}\n"
    return f"{block}\n"


def lookalike_entries(crontab_text):
    """Foreign cron lines that appear to run another installation of this
    project (e.g. an old checkout under a different directory). They are
    never removed automatically - they may be deliberate - only reported."""
    return [
        line for line in crontab_text.splitlines()
        if ("rentczecher" in line or "byt_watchdog" in line)
        and not line.lstrip().startswith("#")
        and line.strip()
    ]


def read_crontab():
    # `crontab -l` exits nonzero when the user has no crontab yet.
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def write_crontab(text):
    result = subprocess.run(["crontab", "-"], input=text, text=True)
    if result.returncode != 0:
        fail("failed to write crontab")


def install_cron(interval_hours, dry_run):
    step(f"Registering cron entry (every {interval_hours} h)")
    if shutil.which("crontab") is None:
        fail(
            "crontab was not found on PATH; install cron, or re-run with "
            "--no-cron and schedule the run yourself"
        )
    existing = read_crontab()
    try:
        new_crontab = merge_crontab(existing, interval_hours)
        foreign = strip_legacy_entries(strip_managed_block(existing))
    except ValueError as error:
        fail(str(error))
    suspects = lookalike_entries(foreign)
    if dry_run:
        print("    would install crontab:")
        for line in new_crontab.splitlines():
            print(f"    | {line}")
    else:
        write_crontab(new_crontab)
    for line in suspects:
        print(f"    WARNING: crontab line looks like another installation of this project;\n"
              f"             remove it manually if that is not intended:\n"
              f"             {line}")


def smoke_check(dry_run):
    step("Verifying the installed entry point")
    if dry_run:
        print(f"    would run: {ENTRY_POINT} --help")
        return
    result = subprocess.run([str(ENTRY_POINT), "--help"], capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        fail(f"{ENTRY_POINT} --help failed - installation is broken")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Install rentczecher")
    parser.add_argument("--no-cron", action="store_true",
                        help="Skip crontab registration")
    parser.add_argument("--interval-hours", type=int, default=3,
                        help="Scrape interval for the cron entry (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without changing anything")
    args = parser.parse_args(argv)
    if not 1 <= args.interval_hours <= 24:
        parser.error("--interval-hours must be between 1 and 24")
    return args


def print_next_steps(config_state, dry_run):
    if dry_run:
        step("Dry run complete - nothing was changed")
        print("    install for real: ./install.py")
        return
    step("Done")
    if config_state == "created":
        print(f"    1) edit {CONFIG} - SMTP credentials and your search profiles")
        print(f"    2) test it: {ENTRY_POINT} --dry-run")
    else:
        print(f"    test it: {ENTRY_POINT} --dry-run")


def main(argv=None):
    check_python()
    args = parse_args(argv)
    check_uv()
    sync_environment(args.dry_run)
    ensure_data_dir(args.dry_run)
    config_state = ensure_config(args.dry_run)
    if args.no_cron:
        step("Skipping cron registration (--no-cron)")
    else:
        install_cron(args.interval_hours, args.dry_run)
    smoke_check(args.dry_run)
    print_next_steps(config_state, args.dry_run)


if __name__ == "__main__":
    main()
