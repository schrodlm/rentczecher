# Contributing to rentczecher

Thanks for wanting to help. This page gets you from a fresh clone to a change
ready for review.

## The parts

| | What it is | Stack |
|---|---|---|
| `engine/` | Scans the portals, folds the same flat into one, keeps the history, serves it all through an HTTP API | Python, FastAPI, SQLite |
| `panel/` | The app's interface | SvelteKit, TypeScript |
| `shell/` | The desktop window, which starts the engine and hosts the panel | Tauri, Rust |

[docs/architecture.md](docs/architecture.md) shows how they fit together, and
each part has its own `ARCHITECTURE.md`. The [glossary](CONTEXT.md) defines the
words the code uses, and the decisions that bind the design are the ADRs in
[docs/adr/](docs/adr/).

## Setup

You need:

- Python 3.11 or newer and [uv](https://docs.astral.sh/uv/)
- Node.js 20 or newer with npm 9.5 or newer
- Rust 1.90 or newer, through [rustup](https://rustup.rs)
- On Linux, the webview development libraries Tauri compiles against

Then, from the repository root:

```bash
python3 scripts/bootstrap.py
```

It checks the tools, names anything missing and how to install it, installs
the engine and panel environments and the commit hooks. It is safe to run
again at any time.

## Running the app

```bash
(cd panel && npm run tauri dev)
```

This starts the panel's dev server, the shell and the engine in one window.

### Scenarios

Never develop against your real database. A scenario opens the app on a known,
made-up inbox instead: empty, fresh listings, price drops, a disappeared
listing, or the same flat on two portals.

```bash
(cd panel && RENTCZECHER_SCENARIO=price-drops npm run tauri dev)    # Linux, macOS
```
```powershell
cd panel; $env:RENTCZECHER_SCENARIO="price-drops"; npm run tauri dev  # Windows
```

Each scenario is a YAML file in `engine/tests/scenarios/` that states what
happened: the profile's search, the listings each scan saw, then what you did
with them. The app replays it into a scratch database, so your real data is
never touched, and the tests start from the same files. To add one, write a
new file next to the others. `fresh-scrape.yaml` shows every part. A bug in the
interface is best reproduced as a scenario first.

## Tests

```bash
(cd engine && uv run pytest)           # the offline suite, fast, no network
(cd engine && uv run pytest -m live)   # against the real portals, run it deliberately
(cd panel && npm run check)            # types, as CI runs it
(cd panel && npm test)                # the panel's tests
```

Tests live next to what they test, one file per module, named for the
behaviour they pin. Tests that need something special to run have their own
folder: `engine/tests/live/` reaches the real portals, and
`engine/tests/smoke/` runs the frozen engine, see
[docs/development.md](docs/development.md).

## How changes are made

- **Commits are small and atomic.** One logical change per commit, with a
  one-line message in the imperative ("Keep Sreality off in new profiles").
- **Tests come in their own commit**, right after the change they cover.
- **Engine and panel changes are separate commits**, even when one feature
  needs both.
- **Moves and renames are their own commits**, so their diff reads as pure
  movement.
- **The commit hooks must pass.** They run ruff, mypy, the offline tests, the
  locale check and file hygiene. Run them by hand with
  `uv run --project engine prek run --all-files`.

The code style is written down in [CLAUDE.md](CLAUDE.md). In short: plain code
a reader and a type checker can follow over clever code, names that make
comments unnecessary, and comments only for a constraint the code cannot
express. What a portal does stays in that portal's scraper.

Some numbers are tuned against real outcomes, the dedup matcher's weights and
the scoring thresholds among them. Pin today's behaviour with boundary tests
before you move one.

Everything the user reads is written in English and translated in
`panel/locales/cs.po`.

## Finding something to work on

Issues are on [GitHub](https://github.com/schrodlm/rentczecher/issues), and the
order of upcoming work is in the milestones. If you plan something bigger,
open an issue first so we can agree on the shape before you write it.

Whatever you add has to fit how rentczecher uses the portals: one person's own
search, nothing shared or republished, and no way around a portal's refusal.
[ADR 12](docs/adr/0012-one-private-copy-per-person.md) has the rules.
