# rentczecher

A local-first watchdog for the Czech rental and property market. It scrapes the
major Czech portals on a schedule, folds the same property listed on several of
them into one, scores each result against your preferences, and emails you the
new listings and price drops. Nothing else. No daily digest of things you've
already seen.

It runs as a cron one-shot on your own machine. No account, no server, nothing
hosted. Your searches and your history stay on your disk. The emails are in
Czech (the product still calls itself **Byt Watchdog** there). The code and
config are in English.

> **Status:** actively developed, single-maintainer hobby project. What's below
> is what runs today. A larger rewrite of the storage and deduplication
> internals is in progress underneath it. See [ARCHITECTURE.md](ARCHITECTURE.md)
> if you want to work on the code rather than just run it.

## What it does

- **Three portals.** Sreality.cz (JSON API), Bezrealitky.cz (server-rendered
  Next.js data), RE/MAX Czech (HTML). Each is a separate scraper. If one breaks
  or a site is down, the others still run and you still get email.
- **Any search, described once.** A profile says what you're looking for (offer
  type, estate type, a place, price bounds, minimum size or land) and which
  portals to ask. You never paste portal-specific URLs or region ids. A place
  name is resolved to each portal's own search parameters for you.
- **Any Czech location by name.** `place: praha-7`, `place: domazlice`,
  `place: "okres Beroun"`, `place: plzensky`. Any Czech kraj or district as a
  slug or free text. A typo fails loudly with a did-you-mean suggestion instead
  of silently searching the wrong place.
- **Multiple independent profiles.** Flat rentals in Praha 7 to you and your
  partner, houses for sale in Domažlice to your father. Each has its own portals,
  filters, scoring, and recipients, all from one config file and one cron entry.
- **Cross-portal dedup.** The same flat posted on Sreality and Bezrealitky is
  reported once, with a "také na: …" badge, keeping whichever copy carries more
  detail.
- **Preference scoring.** A 0–100 score per listing from weights you set (price
  per m², disposition, size, neighbourhood, land area, total price). The email is
  sorted best-first and shows the score on each card.
- **Price drops and disappearances.** A listing whose price fell since you last
  saw it comes back flagged with the old price. A listing gone for three
  consecutive runs is reported as disappeared. Three misses filters out portal
  API flicker.
- **Prague tram enrichment (optional).** Prague profiles can annotate each
  listing with its nearest tram stop and lines.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `cron` for scheduled runs, or schedule it yourself
- An SMTP account for sending mail (Gmail with an app password works)

## Install

```bash
./install.py            # uv sync, create config from the example, register cron
./install.py --dry-run  # show exactly what it would do, change nothing
```

The installer runs `uv sync`, creates `config.yaml` from `config.example.yaml`
if you don't have one (it never overwrites an existing config), registers a
single cron entry (every 3 h by default, set with `--interval-hours N`, or skip
it with `--no-cron`), and smoke-tests the installed entry point.

Then edit your config and try a run that changes nothing:

```bash
# 1) fill in SMTP credentials and your search profiles
$EDITOR ~/.config/rentczecher/config.yaml

# 2) check it: typos and bad values are reported with the exact offending key
.venv/bin/rentczecher config validate

# 3) dry run: scrape and print results, send no email, write no state
.venv/bin/rentczecher --dry-run
.venv/bin/rentczecher --dry-run --profile praha7-byty   # just one profile
```

## Configuring your search

The config has one shared `email` block, an optional `schedule`, and any number
of named `profiles`. Each profile is a self-contained search.

```yaml
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "you@gmail.com"
  smtp_password: "your-app-password"
  from: "you@gmail.com"

schedule:
  cron_interval_hours: 3          # informational; the cron entry is what runs

profiles:
  praha7-byty:
    name: "Praha 7 – byty k pronájmu"
    enabled: true
    to: ["you@gmail.com", "partner@gmail.com"]

    search:
      offer_type: rent            # rent | sale
      estate_type: flat           # flat | house | land | cottage
      place: praha-7              # any Czech kraj or district; typos get suggestions
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

    tram_enrichment: true         # nearest Prague tram stop on each card

  domazlice-domy:
    name: "Domažlicko – domy a chalupy"
    to: ["father@gmail.com"]

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

`config.example.yaml` is the full reference with every option and its default.

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
rentczecher --dry-run                # scrape + print, no email, no state written
rentczecher --dry-run --profile X    # dry-run a single profile
rentczecher config validate          # validate config.yaml (--path checks another file)
rentczecher db migrate               # create/upgrade the SQLite schema (see note below)
```

Use `.venv/bin/rentczecher` if `.venv` isn't on your `PATH`.

> **On `db migrate`:** the SQLite database it creates is part of a storage
> rewrite that isn't wired into the running tool yet. Today every run reads and
> writes per-profile `seen-*.json` files, and `db migrate` produces an empty
> database that nothing populates. You don't need it to use rentczecher. See
> [ARCHITECTURE.md](ARCHITECTURE.md).

## Where things live

By default rentczecher follows the XDG base directories:

| | Default path |
|---|---|
| Config | `~/.config/rentczecher/config.yaml` |
| Data (history, pid lock, logs) | `~/.local/share/rentczecher/` |
| Cron log | `~/.local/share/rentczecher/cron.log` |

Override order: the `RENTCZECHER_CONFIG` and `RENTCZECHER_DATA_DIR` environment
variables win outright. Otherwise, if a `config.yaml` sits at the repo root, both
config and data resolve there, which is handy for a self-contained checkout.
Otherwise the XDG defaults above. Data always follows the config anchor, so one
installation never splits its history across two homes. The installer warns you
if it finds stranded history from an earlier repo-local setup.

```bash
tail -f ~/.local/share/rentczecher/cron.log   # watch the scheduled runs
```

## Locations

`place:` is resolved against a shipped table,
`src/rentczecher/adapters/scrapers/location_data/places.json`, that maps every
Czech kraj and district to each portal's own search ids. **It is generated.
Never hand-edit it.** Regenerate it when a portal renumbers its taxonomy. The
symptom is a place that used to return listings suddenly returning zero, or the
`live` id tests failing:

```bash
uv run python scripts/refresh_location_data.py places
```

The script harvests each portal's own taxonomy, joins the three by place name,
live-verifies every id against the portal, and refuses to write on a mismatch, so
a regeneration takes a few minutes. `overrides.json` beside the table is the only
hand-maintained part. Its `why` key documents the one Prague id quirk it exists
for. Review the `places.json` diff before committing. On a no-op run the only
line that changes is `generated_at`.

## Development

```bash
uv sync && uv run prek install   # deps + pre-commit hooks
uv run pytest                    # offline test suite (fast, no network)
uv run pytest -m live            # live portal tests, hits the real sites, run deliberately
uv run prek run --all-files      # ruff, mypy, offline pytest, file hygiene (the commit gate)
```

Commits are gated by the pre-commit hooks, and the offline suite must be green.
The dedup matcher's weights and thresholds are calibrated against owner-labeled
listing pairs: `scripts/matcher_eval.py` replays the matcher over every reviewed
pair - run it before and after any tuning.
[ARCHITECTURE.md](ARCHITECTURE.md) maps the code, the module layout, and the
storage rewrite in progress. `CLAUDE.md` records the coding stances this repo
holds to.

## Troubleshooting

- **A scraper suddenly returns 0 results.** Usually the portal changed its page
  structure or ids. `config validate` and `--dry-run` show which portal. If it's
  a location taxonomy change, regenerate `places.json` (above).
- **Sreality returns all 404s.** Sreality's API blanket-404s some networks
  (datacenter and VPN egress) while its homepage serves 200 fine. This is almost
  always your connection being blocked, not a bug. It works from ordinary
  residential connections.
- **No email arrived but the log shows new listings.** Check the SMTP block.
  Gmail needs an app password, not your account password. The email is only sent
  when there's something new or a price drop. A run that finds only already-seen
  or only disappeared listings sends nothing by design.

## License

Not yet chosen. The project is intended to be free and open source. If you're
looking at this before a `LICENSE` file lands, ask.
