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
  type, estate type, a place, price bounds, minimum size or land) and which
  portals to ask. You never paste portal-specific URLs or region ids. A place
  name is resolved to each portal's own search parameters for you.
- **Any Czech location by name.** `place: praha-7`, `place: domazlice`,
  `place: "okres Beroun"`, `place: plzensky`. Any Czech kraj or district as a
  slug or free text. A typo fails loudly with a did-you-mean suggestion instead
  of silently searching the wrong place.
- **Multiple independent profiles.** Flat rentals in Praha 7, houses for sale in
  Domažlice. Each has its own portals, filters, and scoring, all from one config
  file and one cron entry.
- **Cross-portal dedup.** The same flat posted on Sreality and Bezrealitky is
  shown once, with links to its other portals, keeping whichever copy carries
  more detail.
- **Preference scoring.** A 0–100 score per listing from weights you set (price
  per m², disposition, size, neighbourhood, land area, total price). It is
  computed but not shown anywhere yet.
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
cp engine/config.example.yaml ~/.config/rentczecher/config.yaml
```

For scheduled runs, register a cron entry yourself pointing at
`engine/.venv/bin/rentczecher` (a packaged desktop app with its own scheduling is
in the works).

Then edit your config and try a run that changes nothing:

```bash
# 1) fill in your search profiles
$EDITOR ~/.config/rentczecher/config.yaml

# 2) check it: typos and bad values are reported with the exact offending key
engine/.venv/bin/rentczecher config validate

# 3) dry run: scrape and log the counts, write no state
.venv/bin/rentczecher --dry-run
.venv/bin/rentczecher --dry-run --profile praha7-byty   # just one profile
```

## Configuring your search

The config has an optional `schedule` and any number of named `profiles`. Each
profile is a self-contained search.

```yaml
schedule:
  cron_interval_hours: 3          # informational, the cron entry is what runs

profiles:
  praha7-byty:
    name: "Praha 7 – byty k pronájmu"
    enabled: true

    search:
      offer_type: rent            # rent | sale
      estate_type: flat           # flat | house | land | cottage
      place: praha-7              # any Czech kraj or district, typos get suggestions
      min_price: 0
      max_price: 25000
      dispositions: ["2+kk", "2+1"]   # empty = all
      min_size_m2: 0

    scrapers: [sreality, bezrealitky, remax]

    scoring:
      price_per_m2_weight: 40
      disposition_weight: 30
      preferred_dispositions: ["2+kk", "2+1", "3+kk"]
      size_weight: 15
      ideal_size_m2: 55
      neighborhood_weight: 15
      preferred_neighborhoods: ["Holešovice", "Letná"]

  domazlice-domy:
    name: "Domažlicko – domy a chalupy"

    search:
      offer_type: sale
      estate_type: house
      place: domazlice
      max_price: 5000000
      min_land_m2: 500

    scrapers: [sreality, bezrealitky, remax]

    scoring:
      land_weight: 40
      ideal_land_m2: 2000
      price_weight: 30
      max_good_price: 3000000
      size_weight: 30
      ideal_size_m2: 150
```

`engine/config.example.yaml` is the full reference with every option and its default.

A few things worth knowing:

- **`scrapers` is a list of portal names**, like `[sreality, bezrealitky, remax]`.
  There are no per-portal parameter blocks. The location comes entirely from
  `search.place`.
- **Scoring weights are relative and sum to a ceiling you set.** A component only
  contributes when its weight is set and the listing has the field it needs. No
  land area, and the land component just doesn't fire. Weights that add up to
  about 100 make the score read as a percentage.
- **The config is strictly validated.** An unknown key is an error, not a silent
  no-op. That includes the pre-`place` per-portal keys from very old configs. Run
  `config validate` to see exactly what's wrong before a cron run does.

## CLI

```bash
rentczecher                          # run every enabled profile (what cron calls)
rentczecher --profile praha7-byty    # run one profile
rentczecher --dry-run                # scrape and log counts, no state written
rentczecher --dry-run --profile X    # dry-run a single profile
rentczecher config validate          # validate config.yaml (--path checks another file)
rentczecher db migrate               # create/upgrade the SQLite schema (see note below)
```

Use `engine/.venv/bin/rentczecher` if `engine/.venv` isn't on your `PATH`. The
command comes from the engine's Python package, `rentczecher_engine`.

> **On `db migrate`:** every run applies pending schema migrations on startup,
> so you rarely need this command. It exists to create or upgrade the database
> without scraping (fresh installs, checking a new schema). See
> [engine/ARCHITECTURE.md](engine/ARCHITECTURE.md).

## Where things live

By default rentczecher follows the XDG base directories:

| | Default path |
|---|---|
| Config | `~/.config/rentczecher/config.yaml` |
| Data (history, pid lock, logs) | `~/.local/share/rentczecher/` |
| Cron log | `~/.local/share/rentczecher/cron.log` |

Override order: the `RENTCZECHER_CONFIG` and `RENTCZECHER_DATA_DIR` environment
variables win outright. Otherwise, if a `config.yaml` sits in `engine/`, both
config and data resolve there, which is handy for a self-contained checkout.
Otherwise the XDG defaults above. Data always follows the config anchor, so one
installation never splits its history across two homes. The installer warns you
if it finds stranded history from an earlier repo-local setup.

```bash
tail -f ~/.local/share/rentczecher/cron.log   # watch the scheduled runs
```

## Locations

Places come from the gazetteer, a SQLite file shipped with the engine
(`engine/src/rentczecher_engine/adapters/geocoding/gazetteer.sqlite`). It holds
every official Czech place from the RÚIAN address registry, keyed by its RÚIAN
code, and how each portal names the places it can search by. `place:` names a
kraj, an okres or a Praha obvod (`praha-7`, `domazlice`, `plzensky`).
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
happened: the listings each scan saw, then which ones you viewed. The debug app
replays it through the engine into a scratch folder and runs there, so your real
config and data are never touched. Tests start from the same files. To add one,
write a new file next to the others. `fresh-scrape.yaml` shows every part.

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
  structure or ids. `config validate` and `--dry-run` show which portal. If it's
  a location taxonomy change, rebuild the gazetteer (above).
- **Sreality returns all 404s.** Sreality's API blanket-404s some networks
  (datacenter and VPN egress) while its homepage serves 200 fine. This is almost
  always your connection being blocked, not a bug. It works from ordinary
  residential connections.

## License

Not yet chosen. The project is intended to be free and open source. If you're
looking at this before a `LICENSE` file lands, ask.
