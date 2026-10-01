# 7. A scan notifies before it commits

Status: accepted (2026-07), recorded 2026-10-01

## Context

A scan scrapes, dedups, scores and diffs against what the store has seen, then
tells the user what is new and records it as seen. Either step can fail: the
mail server can be down, a portal can change its markup, one profile's config
can be wrong. A pipeline that looks tidier in another order can quietly lose
a notification, or let one broken portal silence every other.

## Decision

Two rules hold for every scan, whichever interface starts it.

- **Notify, then commit.** The scan persists its outcome only after the
  notification succeeded, or when there was nothing to notify. A failed send
  persists nothing, so the next scan finds the same listings new and tries
  again.
- **Failures stay where they happen.** A scraper that fails is reported
  broken, and the other portals' results still go through. A profile that
  fails is logged, and the other profiles still run.

## Consequences

- A notification can repeat, never vanish: a crash between sending and
  committing sends the same listings again on the next scan.
- A partly broken scan is still a scan. Its run reports which portals failed,
  which is what the panel's portal health shows.
- A dry run neither notifies nor commits, so it is safe against real data.
