# Byt Watchdog

Multi-profile real estate monitor for the Czech Republic. Scrapes major Czech real estate sites, deduplicates, scores, and emails new listings - supports any combination of location, property type, and offer type.

## Features

- **Multi-profile**: Run independent searches in parallel (e.g., flats in Praha 7 + houses in Domažlice)
- **3 sources**: Sreality.cz (API), Bezrealitky.cz (SSR), RE/MAX Czech (HTML)
- **Any property type**: Flats, houses, cottages, land, agricultural estates
- **Any offer type**: Rent or sale
- **Any location**: Any Czech kraj or district by name (`place: praha-7`) - typos get suggestions
- **Smart scoring**: 0-100 score with configurable weights (price/m2, disposition, size, land area, neighborhood, total price)
- **Price drop alerts**: Detects when a listing's price decreases
- **Disappeared listings**: Tracks when properties are removed
- **Cross-source dedup**: Detects same property listed on multiple sites
- **Prague tram enrichment**: Nearest tram stop + lines (for Prague profiles)
- **Google Maps links**: One-click map view per listing
- **Per-profile DB**: Each profile has its own `seen-{id}.json`
- **Per-profile recipients**: Different email recipients per search

## Setup

Requires Python >= 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
# Install (creates .venv, installs deps, copies the example config, sets up cron)
./install.py

# Preview what the installer would do
./install.py --dry-run

# Configure: edit config.yaml (SMTP credentials, search profiles)

# Test without sending email or writing state
.venv/bin/rentczecher --dry-run
.venv/bin/rentczecher --dry-run --profile praha7-byty
```

Development setup:

```bash
uv sync && uv run prek install   # deps + pre-commit hooks
uv run pytest                    # offline test suite
uv run pytest -m live            # live portal tests (deliberate)
```

## Location data

`src/rentczecher/adapters/scrapers/location_data/places.json` maps every Czech
district (14 kraje, 76 okresy, Praha 1–10) to each portal's search ids. It is
**generated — never edit it by hand**. Regenerate it when a portal renumbers
its taxonomy (symptoms: a place that used to return listings suddenly returns
zero, or `pytest -m live` fails in `TestShippedIdsLive`):

```bash
uv run python scripts/refresh_location_data.py
```

The script harvests each portal's own taxonomy, joins the three by place name,
live-verifies every Bezrealitky id against the portal, and refuses to write
anything on a mismatch — expect it to take a few minutes (requests are paced).
`overrides.json` in the same directory is the only hand-maintained part; its
`why` key explains the Prague quirk it exists for. Review the `places.json`
diff before committing a regeneration; on a no-op run the only line that
changes is `generated_at`.

## Config

The config has a shared `email` section and multiple `profiles`:

```yaml
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "you@gmail.com"
  smtp_password: "your-app-password"
  from: "you@gmail.com"

profiles:
  # Flat rentals in Praha 7
  praha7-byty:
    name: "Praha 7 - byty k pronajmu"
    to: ["you@gmail.com", "partner@gmail.com"]
    search:
      offer_type: rent
      estate_type: flat
      place: praha-7
      max_price: 25000
    scrapers: [sreality, bezrealitky, remax]
    scoring:
      price_per_m2_weight: 40
      disposition_weight: 30
      preferred_dispositions: ["2+kk", "2+1"]
      size_weight: 15
      ideal_size_m2: 55
      neighborhood_weight: 15
      preferred_neighborhoods: ["Holešovice", "Letná"]
    tram_enrichment: true

  # Houses for sale in Domažlice district
  domazlice-domy:
    name: "Domažlicko - domy a chalupy"
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

See `config.example.yaml` for a complete reference with all options. Check any
config with `.venv/bin/rentczecher config validate` — typos and invalid values
are reported with the exact offending key.

`place` accepts any Czech kraj or district as a slug or free text ("Praha 7",
"okres Domažlice", "plzensky") and resolves it to each portal's search
parameters; unknown places fail validation with did-you-mean suggestions.

Configs from before the `place` key carried per-portal parameter blocks
(`locality_district_id`, `region_osm_id`, `search_url`, ...); those are
rejected outright — a profile's `scrapers` is a list of portal names and
`search.place` carries the location.

## Adding a new profile

1. Describe the search: `offer_type`, `estate_type`, `place` (any Czech kraj
   or district, e.g. `place: olomouc`), price bounds
2. List the scrapers to run (`scrapers: [sreality, bezrealitky, remax]` -
   no per-portal parameters needed)
3. Configure scoring weights for what matters (price/m2 for rentals, land_area for houses, etc.)
4. Set the `to` recipients

## CLI

```bash
.venv/bin/rentczecher                          # Run all profiles
.venv/bin/rentczecher --profile praha7-byty    # Run one profile
.venv/bin/rentczecher --dry-run                # No email, no DB changes
.venv/bin/rentczecher --dry-run --profile X    # Test one profile
.venv/bin/rentczecher config validate          # Check config.yaml for errors
```

## Logs

The cron log lives in the data directory the installer printed:

```bash
tail -f ~/.local/share/rentczecher/cron.log   # fresh installs
tail -f data/cron.log                         # repo-local setups
```
