# 6. Dedup matches pairs and never groups them transitively

Status: accepted (2026-07), revised 2026-08 and 2026-11, recorded 2026-10-01

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

A pair scoring in the match band merges only when the property itself agrees
as well, on what its estate type carries. The prices must be within 10% of
each other. Flats must give the same disposition and sizes within 6 m².
Houses and cottages must give sizes within 6 m² or plots within 10%, and
dispositions only when both sides give one. Land must give plots within 10%.
A value missing on either side cannot confirm agreement. A pair that scores
as a match without agreeing is recorded as uncertain instead. Closeness alone
used to carry a match: one street within 100 m outscored the match threshold,
so two flats in one building merged even with prices 30% apart.

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
- Properties that a portal describes too thinly to compare, without a price,
  or a flat without a size or disposition, are never merged.
- Two alike flats in one building, with the same layout, size and price,
  still merge. Only something like the photos could tell them apart.
- The weights and band thresholds were calibrated against owner-labeled pairs
  of real listings. They change only with boundary tests pinning current
  outcomes first.
