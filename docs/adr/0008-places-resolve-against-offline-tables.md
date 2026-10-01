# 8. Places resolve against offline tables

Status: accepted (2026-08), recorded 2026-10-01

## Context

Places come up twice. A search names a place, and each portal wants it in its
own form: a numeric district id, a region tree, a region id. A scraped listing
carries a place in each portal's own text format, which dedup must compare
across portals. Both used to be hand-maintained guesses: ids pasted into
config, and a silent fallback to one Prague district when one was missing.

## Decision

Both kinds of place resolve against tables that ship with the app and need no
network.

**Search places.** A generated table, `places.json`, holds every region and
district with each portal's id for it. `engine/scripts/refresh_location_data.py`
harvests it from the portals' own taxonomies and verifies each id live, and
it is never hand-edited. `overrides.json` beside it is the only
hand-maintained part, for ids a portal does not publish. A profile names its
place by slug, and `resolve()` returns one flat, typed row, `PlaceParams`.
Each scraper resolves the place itself at construction and narrows the row
to its own frozen view (`SrealityPlace`, `RemaxPlace`, `BezrealitkyPlace`),
keeping no other portal's data. An unknown place fails loudly, with
suggestions.

**Listing places.** Each scraper parses its portal's location text into a
`ParsedPlace`, with the names deliberately unlabeled, since a name's kind is
discovered by lookup and never assumed. A pipeline stage before dedup
locates each listing against an offline gazetteer built from the state
address registry: text first, then the portal's GPS when the text is
ambiguous. When neither can be trusted, the listing's place is `None`. The
gazetteer refuses rather than guesses.

## Consequences

- Adding a place is a table refresh, not reconnaissance in a portal's
  network tab.
- Portal knowledge stays in each adapter, and the type checker follows a
  place from the table to the query.
- `PlaceParams` names portals in its fields, because the data it carries is
  per portal by nature.
- Dedup never locates. It reads the place the pipeline stage attached.
- Rejected: a nested per-portal payload behind an opaque resolver, which
  would drop typing to dictionary keys mid-chain for a resolver that never
  names a portal. Injecting the resolved place into each scraper's
  constructor, which would let the spec and its place disagree.
