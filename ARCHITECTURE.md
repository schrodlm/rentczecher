# Architecture

This is the map for working on the code. If you only want to run rentczecher,
[README.md](README.md) is enough. Read this before touching the internals. There
is a live pipeline and a half-built successor sitting side by side in the tree,
and knowing which is which will save you a lot of confusion.

## The one thing to understand first

**Two storage-and-dedup worlds coexist in this repo.**

- The **live pipeline**, what cron actually runs, persists state in per-profile
  `seen-*.json` files and dedups with a scored, strict-pairwise matcher backed
  by an offline geocoder. This is the working product.
- A **canonical-property model** (a real SQLite schema, repositories, cross-run
  geocell candidacy, the dedup audit trail) is being built underneath it. It
  exists and is unit-tested, but it is **inert**. Nothing in the running
  pipeline calls it yet. It's reachable only from `rentczecher db migrate` and
  from tests.

The rewrite lands in small, always-green steps. Each piece ships before its
consumer, tested in isolation, so the tool keeps working the whole time and there
is never a big-bang cutover. When you read a module, the first question to ask is
whether it's on the live path or ahead of its consumer. The map below tells you
for every part.

## Layout

A single installable package with light hexagonal layering:

```
src/rentczecher/
  domain/        frozen dataclasses, pure. no I/O, no deps on adapters
  adapters/      the edges: scrapers, notifiers, config, storage, geocoding
  services/      use-cases over the domain: dedup, scoring, locate
  cli/           argparse entry point. wires adapters to the pipeline
```

- `domain/` never imports from `adapters/` or `services/`. It's just types and
  two geo functions.
- `services/` depends on `domain/` only.
- `adapters/` and `cli/` may depend on everything. `cli/main.py` is where the
  wiring happens.

`pyproject.toml` defines the package and the `rentczecher` entry point. `uv`
manages the lockfile and the dev environment. Lint, type, and test are ruff (a
pinned lenient ruleset), mypy (clean, no ignore list), and pytest.

## The live pipeline

Everything below runs today. The entry point is `cli/main.py::run` →
`run_profile`, called once per enabled profile per cron invocation.

```
config.yaml
   │  load + strict pydantic validation (adapters/config)
   ▼
SearchSpec.from_search_config(profile["search"])        # portal-neutral intent
   │
   ▼
for each scraper in profile["scrapers"]:                # adapters/scrapers
   resolve(spec.place) → per-portal ids                 # location_resolver
   fetch → parse → list[Listing]                         # fetch/parse split
   │      (ScraperBrokenError = contract changed, isolated per scraper)
   ▼
filter by disposition / min size / min land             # _apply_filters
   ▼
enrich_tram(listing)   (Prague profiles only)           # adapters/enrichment
   ▼
locate_listings(listings, gazetteer)                    # services/locate
   ▼
cross_source_dedup(listings, gazetteer)                 # services/dedup
   ▼
compute_score(listing, profile)                         # services/score
   ▼
price drops + new + disappeared                         # adapters/legacy_json_db
   ▼
send_email(...)   then   mark_seen(...)                 # notify-then-commit
```

Two orderings are load-bearing and must be preserved:

- **Notify-then-commit.** State is marked seen only after the email is sent. If
  the send fails, nothing is committed and the same listings are retried next
  run. You never silently swallow a new listing because SMTP hiccuped.
- **Three-miss disappearance.** A listing is disappeared only after three
  consecutive runs without it, to ride out portal API flicker.

`--dry-run` runs the whole thing but skips every write, including the miss-count
increment, so it previews against the last real run's state without corrupting
it.

### Domain types (live)

- `ScrapedListing` (frozen): the immutable facts of one scrape. id, source,
  title, price, location, url, optional size/disposition/gps/land/charges, plus a
  `ParsedPlace` (the raw place names the scraper pulled out).
- `ListingAnnotations` (frozen): the pipeline's conclusions. score,
  `price_drop_from`, nearest stop, `cross_source`, and `place` (the
  gazetteer-resolved location; `None` means unlocatable, not unasked).
- `Listing`: wraps the two. Construct with `Listing.build(**flat_fields)` and
  never mutate. `with_annotations(...)` returns a new `Listing` sharing the same
  facts. Every field of both inner records is exposed as a read-only property.
  The facts-vs-conclusions split with copy-on-write is deliberate. A re-scrape
  replaces facts, the pipeline replaces annotations, and the two never tangle.
- `SearchSpec`: portal-neutral search intent, built once per profile and handed
  to every scraper, the filter, and the email.

### Scrapers

Each portal is a `BaseScraper` subclass registered in `ALL_SCRAPERS`. They share
one `httpx.Client` from `client.build_client()` (browser User-Agent, 30 s
timeout, connect retries). Two design points matter:

- **Fetch/parse split.** `_fetch_page` is the only code that touches the network.
  Parsing is a pure function over the fetched bytes or JSON. That's what lets the
  parser tests run fully offline against recorded fixtures (`tests/fixtures/`)
  via an injected `httpx.MockTransport`, with no live calls in the default suite.
- **`ScraperBrokenError` is not the same as empty.** A portal responding in a
  shape the parser no longer understands (missing pagination keys, missing
  `__NEXT_DATA__`) raises `ScraperBrokenError`, isolated to that scraper. A
  genuinely empty result is different and is not an error. RE/MAX is the
  exception: a cardless HTML page is indistinguishable from zero results there,
  so it can't raise it.

The portals, briefly. **Sreality** speaks its JSON API (`/api/v1/estates/search`,
needs a browser UA). **Bezrealitky** is server-side Next.js: parse the
`__NEXT_DATA__` blob and walk the Apollo cache. **RE/MAX** is HTML parsed with
BeautifulSoup. All three do client-side price filtering on top of the portal's
price params, because those params aren't reliable.

### Location resolution

`location_resolver.resolve(place)` turns a place slug or free-text name into a
`PlaceParams` row from the shipped table
(`adapters/scrapers/location_data/places.json`), or raises `PlaceNotFoundError`
with did-you-mean suggestions. Each scraper narrows that to its own typed view
(`SrealityPlace`, `BezrealitkyPlace`, `RemaxPlace`) at construction and keeps no
other portal's data. `places.json` is generated and live-verified by
`scripts/refresh_location_data.py`. Never hand-edit it. `overrides.json` beside
it is the only hand-maintained part (the Bezrealitky Prague id quirk).

Config loading resolves every profile's `place` up front, so an unresolvable
place is a config error before any scraper runs.

### Offline geocoder (RÚIAN gazetteer)

`adapters/geocoding/gazetteer.py` resolves a listing's scraped place names to a
single Czech place with a centroid (lat/lon), **entirely offline**. The data is a
bundled read-only SQLite file (`gazetteer.sqlite`, about 21 MB, roughly 105k
places) generated from the RÚIAN state address registry by
`scripts/refresh_location_data.py gazetteer`. Resolution is deliberately
conservative: ambiguous names resolve to `None` rather than guessing. Name-tier
lookups are municipality-scoped, so another town's street name can never
impersonate street-level evidence for a Prague neighbourhood.

`services/locate.py::locate(listing, gazetteer)` sits on top: text resolution
first, reverse geocoding when the text is ambiguous but the portal gave GPS.
`locate_listings` runs as a pipeline stage before dedup, landing the result as
the `place` annotation that dedup and everything after read location from.

### The scored matcher

`services/dedup.py::cross_source_dedup` scores every cross-source pair on five
three-state factors (GPS distance, shared place name, disposition, price, size:
agree positive, disagree negative, missing exactly zero), gated by an evidence
floor. Pairs merge only above the confident-match threshold; an **uncertain
band** below it is scored and recorded but never merges — a wrong merge hides a
listing, a missed one only repeats it. The weights and thresholds are calibrated
against owner-labeled real cross-portal pairs; `scripts/matcher_eval.py` replays
the matcher over every reviewed pair and runs before and after any tuning.

### Config

`adapters/config/schema.py` is the single source of truth for config shape,
defaults, and normalization. Strict pydantic v2 (`extra="forbid"`, so a typo is
an error with a suggestion). `loader.py` validates, cross-checks each `place`,
and returns a plain dict with the SMTP secret unwrapped. `paths.py` resolves
config and data locations (env overrides, then repo-local if a config is there,
then XDG).

### Notification and enrichment

`adapters/notifiers/smtp.py::send_email` builds one Czech HTML and text email per
profile: score-sorted cards with image, price (and old price on a drop), details,
source and cross-source badges, a Google Maps link (address-based, GPS as
fallback), and an optional disappeared section.
`adapters/enrichment/metro.py::enrich_tram` annotates a listing with its nearest
tram stop. Note it's a hardcoded Praha-7-area stop table (the module is named
`metro` but holds tram data), so it's only meaningful for Prague profiles.

## The inert successor

None of this is on the live path yet. It's built ahead of its consumers, on
purpose.

### SQLite canonical-property model

A relational schema where a **property** is the inferred real-world unit and a
**listing** is one portal's posting of it. The same flat on two portals is one
property with two listings, and cross-portal disagreements are recorded as an
audit trail rather than destructively merged. The tables and their relationships
are documented in [SCHEMA.md](SCHEMA.md). Migration `0001_init.sql` is the
authoritative DDL.

`adapters/repositories/` holds the repository interfaces and their SQLite
implementations (`SqliteListingRepository`, `SqlitePropertyRepository`), plus the
connection setup and the migration runner. These follow the repo's
static-readability stance to the letter: `row_factory = sqlite3.Row`, a
`_to_<type>(row)` mapper naming every field, full column lists spelled out, no
reflection. `rentczecher db migrate` applies the migrations. **Nothing writes to
these tables in a normal run.** The live pipeline still persists through
`adapters/legacy_json_db.py`, which knows nothing about the domain types.

### Geocell blocking, dormant

`domain/geo.py` carries the `geocell` blocking grid (a roughly 1.2 km cell key)
used for near-point candidate lookup. Migration `0002` adds the cell columns to
`properties` and `find_candidates` queries a cell and its eight neighbours, but
nothing on the live path calls either — blocking becomes load-bearing when
cross-run property resolution wires in.

## Where the work is now

The **dedup matcher rewrite** (1.7.6 in the project's own numbering) just
landed: the hard-gate matcher became the scored multi-factor one described
above. No factor ever compares a raw portal string. Every input passes a
normalizer whose contract is canonical-or-None, and `None` means the factor
abstains rather than vetoes. Location and disposition are normalized (via the
gazetteer and a synonym table), price and size are numeric, and nothing else is
load-bearing for v1. Geospatial blocking over the gazetteer is what will make
cross-run, cross-profile property resolution tractable.

One rule is permanent and predates this work: **strict pairwise matching, no
transitive grouping.** Transitive grouping shipped once, merged unrelated
listings in production, and was reverted. It stays reverted. Any move back to
union-find is gated on proving it matches or beats the current precision on a
labelled sample first.

Next in sequence: wire storage in (the JSON to SQLite cutover, with dry-run,
backup, and a guard that refuses if a cron run may be mid-write), then extract
the orchestration into a `services/pipeline.run_profile` that the CLI and,
later, a GUI both call.

### The bigger arc

rentczecher is on a long road from a cron script for one household to a public,
aggregate-only observatory of the Czech housing market. The seams are being built
in order:

1. **Foundations** (where we are): the package, the frozen domain model, the
   location resolver, SQLite and migrations, the scraper framework with recorded
   fixtures.
2. **Robustness**: a real test pyramid (pure unit, recorded-fixture contract,
   nightly live-drift, e2e), property tests, boundary pins on the tuned dedup and
   scoring constants, CI.
3. **Quick-glance UX**: a settled card design, a better email, non-SMTP channels
   (Telegram, ntfy, webhook), score explainability.
4. **Desktop app**: a Tauri and SvelteKit shell over a Python sidecar that
   imports this exact `services` layer, with a signed auto-updater (scrapers rot,
   and fixes have to reach non-technical users on their own). The package is the
   product, the GUI is a client.
5. **Adoption**: landing site, docs, a staged launch. Free and open source.
6. **Platform**: a website publishing rigorous, novel statistics (time-on-market
   survival, price-cut hazard, delisting dynamics) fed by opted-in users' local
   runs. Aggregate-only, never re-serving individual listings, always
   deep-linking back to the portals.

That's why the domain model, the append-only price series, and the location
resolver exist well before anything uses them the obvious way. Each is a seam a
later phase consumes. The detailed roadmap and the binding architecture decisions
live in a separate planning repository outside this tree. The summary above is
enough to orient a contributor.

## Conventions worth knowing before you send a patch

- **Static readability over cleverness.** Spell things out. Prefer code a type
  checker verifies over terse indirection. The SQLite repositories are the worked
  example: no `dataclasses.fields()` tricks, no placeholder-string hacks, the
  column list is the source of truth.
- **Comments state constraints the code can't express**, like a portal quirk or a
  deliberate trade-off. Not a paraphrase of the line below, and never a pointer to
  a plan, milestone, or commit.
- **Atomic, one-line commits.** A fix and its regression test go together. Two
  fixes never do.
- **Tests pin accepted behavior, per module.** A regression test lives in the
  owning module's test file, named for the behavior it pins, not in a bug- or
  milestone-themed catch-all. Scoring thresholds are tuned-by-feel production
  values — pin them with boundary tests before touching them. The dedup
  matcher's weights and thresholds are calibrated against owner-labeled pairs —
  move them only with `scripts/matcher_eval.py` evidence.
- **User-facing strings are Czech. Code and internal strings are English.**

`CLAUDE.md` has the full text of these stances.
