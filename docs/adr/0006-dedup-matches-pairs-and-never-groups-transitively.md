# 6. Dedup matches pairs and never groups them transitively

Status: accepted (2026-07), revised 2026-08, recorded 2026-10-01

## Context

The same flat is often listed on several portals, with differing titles,
sizes, prices and locations. Dedup folds these into one listing so the user
sees each flat once. Folding by transitive grouping, where A matching B and B
matching C puts A, B and C in one group, was shipped once and reverted, after
it merged unrelated listings in production. One borderline pair is enough to
chain two different flats together.

## Decision

Dedup judges every cross-portal pair on its own evidence and merges only pairs
it is confident about. Two listings from the same portal are never merged.

Each pair gets a score from several weighted factors: location agreement at
the most specific shared tier, price, size, disposition and street names. The
score falls into one of three bands:

- Match: the pair merges, and the listing with more data survives, carrying
  the other's portal as a cross-source mark.
- Uncertain: the pair stays separate and is recorded for audit.
- Different: the pair stays separate.

Every merge is recorded with its score, so any merge can be explained after
the fact.

Grouping is never inferred. A matching B and B matching C does not merge A
with C unless the pair A and C scores as a match itself. Transitive grouping,
such as union-find, comes back only with evidence: it must match or beat
pairwise precision on owner-labeled pairs, and correctly keep apart the
chains that caused the original revert.

## Consequences

- A wrong merge hides a real listing from the user, while a missed merge only
  shows one flat twice. The design accepts more duplicates to avoid hidden
  listings.
- A flat on three portals can survive as two listings when one of its pairs
  falls short of the match band.
- The weights and band thresholds were calibrated against owner-labeled pairs
  of real listings. They change only with boundary tests pinning current
  outcomes first.
