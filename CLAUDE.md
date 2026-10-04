# CLAUDE.md

Multi-profile Czech real-estate watchdog: scrapes portals (Sreality, Bezrealitky, RE/MAX), dedups across them, scores against per-profile preferences, and serves new listings and price drops through its API for notification channels to consume. The binding architecture decisions are the ADRs in `docs/adr/`. Read the ones touching an area before architectural work there. The order and scope of upcoming work live in the GitHub milestones.

Standard clean open-source development practices are the baseline everywhere; the rules below are hard stances on top of that.

## Code style

- **Static readability over cleverness.** Prefer code a reader can follow top-to-bottom and a type checker can verify over a terser form that saves lines by being indirect. Spell things out: name every field, list every column, avoid reflection and metaprogramming that trade a compile-time error for a runtime surprise. A few extra lines that fail loudly and read plainly beat a clever one-liner that fails silently.
- **Code is self-documenting first.** Pick names and structure so a comment is unnecessary. If you feel the need to explain *what* code does, rewrite the code instead of commenting it.
- **Cohesive things live in a class.** State and the operations on it (a store, a client, a resolver) form a class with a small surface, not loose functions threading shared arguments through a module. `cli/main.py` orchestrates and owns no logic of its own.
- **Comment to state a constraint the code cannot express** — an external system's quirk, a deliberate trade-off, a non-obvious consequence. One or two lines, directly above the code they govern.
- **Comments never name what is scheduled to die.** A comment must stay true after planned removals land. Naming a thing a later milestone deletes (a legacy store, a workaround being retired) plants a reference that rots. State the constraint without the doomed name.
- **Short narrating comments are allowed when they genuinely speed up reading** — a section marker in a long parse routine ("# Resolve main image") earns its place; a line-by-line paraphrase never does. Short, on point, at the right spot.
- **Never reference documents from code.** No plan files, milestones, issue numbers, commit hashes, or anything else with a different lifespan than the source. A comment pointing at a plan file or "Milestone 1.5" is wrong even while it is accurate. (Docs referencing docs is fine; commit messages referencing anything is fine.)
- **No reviewer-facing commentary in code.** Never explain what changed, what the old code did, or why the change is correct — that belongs in the commit message and dies there.
- **Portal knowledge stays in the portal's adapter.** Domain and services code never names a portal or narrates a scraper's mechanics. A domain rule motivated by one portal's quirk states the constraint generically ("the scraped field may hold a building-type label"); the quirk itself is documented at the adapter that owns it.
- **No dead code in a commit.** Before committing, re-read the diff and delete anything nothing references — an unused constant, helper, import, or field left from an approach you abandoned mid-change. Ruff catches unused locals and imports but not module-level names, so this is a manual pass every time, not an optional one.

## Commits

- **Atomic.** One logical piece of work per commit, as small as coherent. Two fixes never share a commit.
- **Tests are their own commit.** The implementation lands first; its tests follow immediately in a separate commit, never mixed into it.
- **No AI trailers.** Commit messages carry no Co-Authored-By or session trailers — the subject line is the whole message.
- **Fixups fold in.** A correction to a commit that has not been pushed belongs squashed into it — history records the corrected work, not the correction process.
- **Moves and renames are their own commits.** Relocating or renaming a class, function, or file is one mechanical commit whose diff reads as pure movement; the behavior change that motivated it comes separately.
- **One-line messages.** The subject states the commit's single goal in imperative mood. If the message needs a body to enumerate what changed, the commit is too big — split it.
- **Two reviewers gate every commit.** Before a commit is made, two independent review passes run over the diff: one hunting correctness bugs, one hunting simplifications. Every finding is fixed or explicitly dismissed first.

## Tests

- **Organized by module or feature** (`engine/tests/test_<module>.py`). A regression test lives in the owning module's test file, named for the behavior it pins — never in a bug- or milestone-themed catch-all file.
- **Tests that need something special to run get their own folder**, whose `conftest.py` marks every test in it: `engine/tests/live/` hits real portals, `engine/tests/smoke/` runs the frozen sidecar and needs a freeze first. The folder states the need, so no test is classified by judgment.
- **Test docstrings state the behavior being pinned**, in present tense. Not the history of the bug, not where it was planned.
- **Tests wait for accepted design.** While a change is still being iterated on with the owner, don't write new tests or chase broken ones — tests pin accepted behavior, not drafts. Once the design is accepted, write and fix them; they must be green by commit time (the hooks enforce it).

## Working here

- Layout: `engine/` is the Python engine, its own uv project (package `rentczecher_engine`, which provides the product's `rentczecher` command). `panel/` is the SvelteKit panel. `shell/` is the Tauri shell, driven from the panel with `npm run tauri`.
- Dev setup: `python3 scripts/bootstrap.py` — checks tools, installs the engine and panel environments, and installs the commit hooks. Idempotent, rerun anytime. Commits are gated by pre-commit hooks (ruff, offline pytest, file hygiene, panel locale coverage — see `.pre-commit-config.yaml`); run them manually with `uv run --project engine prek run --all-files`.
- Scenarios (`engine/tests/scenarios/*.yaml`) state what happened, scans then user actions, and replay through the engine's own pipeline. Reproduce a UI state or a bug as a scenario, and open the app on it with `RENTCZECHER_SCENARIO=<name> npm run tauri dev` in `panel/`, never against the real database. Tests start from the same scenarios.
- Offline tests: `uv run pytest` inside `engine/` (live portal tests are excluded by default via the `live` marker). Run live tests deliberately: `uv run pytest -m live`.
- Sreality's API blanket-404s some networks while the homepage serves 200. A sudden all-404 from sreality is usually the egress being blocked, not broken code. Portal investigation notes live in `docs/portals/`.
- The gazetteer (`engine/src/rentczecher_engine/adapters/geocoding/gazetteer.sqlite`) is built by `uv run python -m scripts.gazetteer build` inside `engine/` from RÚIAN and a live portal harvest, and never hand-edited. A place is identified by its RÚIAN kind and code, never by name (ADR 8, `docs/places.md`). Changing `schema.sql` or `normalize_name` means bumping `SCHEMA_VERSION` in `gazetteer.py` and rebuilding.
- SQLite repositories apply the static-readability stance concretely: set `conn.row_factory = sqlite3.Row` and index columns by name; give each row-to-domain conversion a `_to_<type>(row)` mapper that names every field; assign each SQL statement to a `stmt` local (triple-quoted for multi-line); and spell out column lists in full. No `dataclasses.fields()` reflection, no `"?" * len(...)` placeholder tricks — the column list is the source of truth and drift should fail loudly. Write methods never call `conn.commit()` themselves; the caller owns the transaction boundary with one explicit commit per unit of work.
- Scoring thresholds are tuned-by-feel production behavior. Never retune or restructure them without boundary tests pinning current behavior first.
- The dedup matcher's weights and thresholds are calibrated against owner-labeled listing pairs. Move them only with boundary tests pinning current outcomes first, never by feel.
- User-facing strings are written in English and translated through the panel's locale catalogs. Engine output, identifiers and internal strings are English.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, driven via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
