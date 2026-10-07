# rentczecher

A local-first watchdog for the Czech rental and property market. It scrapes the
major Czech portals on a schedule, folds the same property listed on several of
them into one, scores each result against your preferences, and tracks the new
listings and price drops.

It runs as a cron one-shot on your own machine. No account, no server, nothing
hosted. Your searches and your history stay on your disk.

> **Status:** actively developed, single-maintainer hobby project. What's below
> is what runs today. A desktop GUI is in design on top of the same pipeline.
> See [engine/ARCHITECTURE.md](engine/ARCHITECTURE.md) if you want to work on the code
> rather than just run it.

## What it does

- **Three portals.** Sreality.cz (JSON API), Bezrealitky.cz (server-rendered
  Next.js data), RE/MAX Czech (HTML). Each is a separate scraper. If one breaks
  or a site is down, the others still run.
- **Any search, described once.** A profile says what you're looking for (offer
  type, estate type, a place, price and size ranges, minimum land, the dispositions)
  and which portals to ask. You never paste portal-specific URLs or region ids.
  The place is resolved to each portal's own search parameters for you.
- **Official Czech places.** A search place is a kraj, an okres or a Praha
  obvod. A place no portal searches fails loudly instead of silently searching
  the wrong one.
- **Multiple independent profiles.** Flat rentals in Praha 7, houses for sale in
  Domažlice. Each has its own portals, criteria and preferences, and one cron
  entry scans them all.
- **Cross-portal dedup.** The same flat posted on Sreality and Bezrealitky is
  shown once, with links to its other portals, keeping whichever copy carries
  more detail.
- **Preference scoring.** A 0–100 score per listing from weights you set (price
  per m², disposition, size, preferred places, land area, total price). The
  app computes it in the panel and does not show it yet.
- **Price drops and disappearances.** A listing whose price fell shows its old
  price next to the new one. A listing gone for three consecutive runs counts
  as disappeared in the scan's results. Three misses filters out portal API
  flicker.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20 or newer, and Rust via [rustup](https://rustup.rs), for the desktop app
- On Linux, the webview development libraries the desktop app compiles against
  (`scripts/bootstrap.py` names the missing ones and how to install them)
- `cron` for scheduled runs, or schedule it yourself

## Install

```bash
python3 scripts/bootstrap.py   # checks tools, installs the environments
```

For scheduled runs, register a cron entry yourself pointing at
`engine/.venv/bin/rentczecher` (a packaged desktop app with its own scheduling is
in the works).

With at least one profile in the database (see [Profiles](#profiles)), try a
run that changes nothing:

```bash
# dry run: scrape and log the counts, write no state
engine/.venv/bin/rentczecher --dry-run
engine/.venv/bin/rentczecher --dry-run --profile <profile id>   # just one profile
```

## Profiles

Profiles are user data in the database, created, edited and deleted through
the engine's API (`/v1/profiles`). The app's editor screen (issue #11) will be
built on it. Places are picked from the gazetteer through `/v1/places`, which
finds real places by the start of their official name, so a profile only ever
holds a place that exists. The full contract is in
[`docs/api/openapi.json`](docs/api/openapi.json).

Each profile is a self-contained search with three parts:

- **Criteria** decide whether a listing is shown: rent or sale, the estate type
  (flat, house, land or cottage), the search place, price and size ranges, a
  minimum land area and the dispositions you accept, such as 2+kk or 3+1. An
  unset bound is no bound, and no dispositions accept any.
- **Portals** are the sites it scans. The location comes entirely from the
  search place.
- **Preferences** only score and order what is shown. Each has a weight, and
  all but price per m² have a setting: an ideal size or land area, a good
  price, and ranked preferred dispositions and places. A weight is never
  negative, and a setting may be empty only while its weight is 0.

The criteria are fixed once a profile is created, since listings already
tracked were found under them. Everything else can change: the name, the
portals, the preferences and whether the profile is paused. Listings from a
portal taken off a profile stay, and new scans just stop visiting it.

A few things worth knowing:

- **Scoring weights are relative.** A component only contributes when its
  weight is set and the listing has the field it needs. No land area, and the
  land component just doesn't fire. Weights that add up to about 100 make the
  score read as a percentage.
- **Preferred places match by location.** A listing matches a preferred place
  when its resolved location is that place or lies inside it. A flat on
  Přístavní matches a preferred obvod Praha 7. A listing with no location
  matches none.

## CLI

```bash
rentczecher                          # scan every unpaused profile (what cron calls)
rentczecher --profile <profile id>   # scan one profile, by its UUID
rentczecher --dry-run                # scrape and log counts, no state written
rentczecher db migrate               # create/upgrade the SQLite schema (see note below)
```

Use `engine/.venv/bin/rentczecher` if `engine/.venv` isn't on your `PATH`. The
command comes from the engine's Python package, `rentczecher_engine`.

> **On `db migrate`:** every run applies pending schema migrations on startup,
> so you rarely need this command. It exists to create or upgrade the database
> without scraping (fresh installs, checking a new schema). See
> [engine/ARCHITECTURE.md](engine/ARCHITECTURE.md).

## Where things live

| | Default path |
|---|---|
| Data (database, pid lock) | `~/.local/share/rentczecher/` |
| Cron log | `~/.local/share/rentczecher/cron.log` |

Set `RENTCZECHER_DATA_DIR` to put the data elsewhere. A checkout whose
`engine/data/` already holds `rentczecher.db` uses that folder instead.

```bash
tail -f ~/.local/share/rentczecher/cron.log   # watch the scheduled runs
```

## Locations

Places come from the gazetteer, a SQLite file shipped with the engine
(`engine/src/rentczecher_engine/adapters/geocoding/gazetteer.sqlite`). It holds
every official Czech place from the RÚIAN address registry, keyed by its RÚIAN
code, and how each portal names the places it can search by.
[docs/places.md](docs/places.md) describes the units, and
[docs/locating.md](docs/locating.md) how a listing's location text becomes them.

**It is built, never hand-edited.** Rebuild it when ČÚZK publishes a new
registry dump worth picking up, or when a portal renumbers its places. The
symptom of the latter is a place that used to return listings suddenly returning
zero, or the `live` search-place tests failing:

```bash
(cd engine && uv run python -m scripts.gazetteer build)
```

The build downloads the registry, harvests each portal's own list of places,
joins every portal place to its official one by name, and verifies the result.
It takes about a minute and needs the portals reachable. Only a fully verified
file replaces the shipped one. [engine/scripts/gazetteer/README.md](engine/scripts/gazetteer/README.md)
has the details.

## Development

```bash
python3 scripts/bootstrap.py              # one-time setup: tools, both environments, hooks
(cd panel && npm run tauri dev)           # the app in its window: Vite, the shell and the engine
(cd engine && uv run python scripts/freeze_sidecar.py)  # freeze the engine for the desktop app
(cd engine && uv run pytest)              # offline test suite (fast, no network)
(cd engine && uv run pytest -m live)      # live portal tests, hits the real sites, run deliberately
uv run --project engine prek run --all-files  # every commit hook (the commit gate)
```

Commits are gated by the pre-commit hooks, and the offline suite must be green.
The dedup matcher's weights and thresholds are calibrated against owner-labeled
listing pairs. Pin current outcomes with boundary tests before moving them.

The repo has three parts: `engine/` (Python), `panel/` (SvelteKit) and `shell/`
(Tauri). [engine/ARCHITECTURE.md](engine/ARCHITECTURE.md) maps the engine's code.
`CLAUDE.md` records the coding stances this repo holds to.

### Scenarios

A scenario opens the app on a known inbox instead of your real data: empty,
fresh listings, price drops, a disappeared listing, or the same flat on two
portals.

```bash
(cd panel && RENTCZECHER_SCENARIO=price-drops npm run tauri dev)    # Linux, macOS
```
```powershell
cd panel; $env:RENTCZECHER_SCENARIO="price-drops"; npm run tauri dev  # Windows
```

Each scenario is a YAML file in `engine/tests/scenarios/` that states what
happened: the profile's search, the listings each scan saw, then which ones you
viewed. The debug app seeds the profile into a scratch database, replays the
scans through the engine and runs there, so your real data is never touched.
Tests start from the same files. To add one, write a new file next to the
others. `fresh-scrape.yaml` shows every part.

## Building the desktop app

```bash
(cd panel && npm run tauri build)                  # every installer format for this OS
(cd panel && npm run tauri build -- --bundles deb) # only the .deb on Linux
```

One command builds the panel, freezes the engine and compiles the shell. The
installers land in `shell/target/release/bundle/`. Each OS builds only
its own installers, since the frozen engine cannot be cross-compiled.

## Troubleshooting

- **A scraper suddenly returns 0 results.** Usually the portal changed its page
  structure or ids. `--dry-run` shows which portal. If it's a location
  taxonomy change, rebuild the gazetteer (above).
- **Sreality returns all 404s.** Sreality's API blanket-404s some networks
  (datacenter and VPN egress) while its homepage serves 200 fine. This is almost
  always your connection being blocked, not a bug. It works from ordinary
  residential connections.

## License

Not yet chosen. The project is intended to be free and open source. If you're
looking at this before a `LICENSE` file lands, ask.
