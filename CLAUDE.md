# CLAUDE.md

Multi-profile Czech real-estate watchdog: scrapes portals (Sreality, Bezrealitky, RE/MAX), dedups across them, scores against per-profile preferences, emails new listings and price drops. The roadmap and binding architecture decisions live in `docs/plans/` — start with `00-roadmap.md` and `decisions.md` before any architectural work.

Standard clean open-source development practices are the baseline everywhere; the rules below are hard stances on top of that.

## Code style

- **Code is self-documenting first.** Pick names and structure so a comment is unnecessary. If you feel the need to explain *what* code does, rewrite the code instead of commenting it.
- **Comment only to state a constraint the code cannot express** — an external system's quirk, a deliberate trade-off, a non-obvious consequence. One or two lines, directly above the code they govern.
- **Never reference documents from code.** No plan files, milestones, issue numbers, commit hashes, or anything else with a different lifespan than the source. A comment pointing at `docs/plans/...` or "Milestone 1.5" is wrong even while it is accurate. (Docs referencing docs is fine; commit messages referencing anything is fine.)
- **No reviewer-facing commentary in code.** Never explain what changed, what the old code did, or why the change is correct — that belongs in the commit message and dies there.

## Commits

- **Atomic.** One logical piece of work per commit, as small as coherent. A fix and its regression test belong together; two fixes never do.
- **One-line messages.** The subject states the commit's single goal in imperative mood. If the message needs a body to enumerate what changed, the commit is too big — split it.

## Tests

- **Organized by module or feature** (`tests/test_<module>.py`). A regression test lives in the owning module's test file, named for the behavior it pins — never in a bug- or milestone-themed catch-all file.
- **Test docstrings state the behavior being pinned**, in present tense. Not the history of the bug, not where it was planned.

## Working here

- Offline tests: `python3 -m pytest tests/ --ignore=tests/test_scrapers_live.py`. `tests/test_scrapers_live.py` hits real portals — run it deliberately, not by habit.
- Sreality's API blanket-404s some networks while the homepage serves 200. A sudden all-404 from sreality is usually the egress being blocked, not broken code.
- Scoring and dedup thresholds are tuned-by-feel production behavior. Never retune or restructure them without boundary tests pinning current behavior first.
- User-facing strings (emails, logs meant for the owner) are Czech; identifiers and internal strings are English.
