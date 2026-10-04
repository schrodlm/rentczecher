# 8. Places are RÚIAN units, resolved offline

Status: accepted (2026-08), revised 2026-10-01

## Context

Places come up three times. A search names a place, and each portal wants it
in its own form: a numeric district id, a region tree, a region id. A scraped
listing carries a place in each portal's own text format, which dedup must
compare across portals. And a profile prefers some places over others within
its search, down to a single street. All three used to be hand-maintained
guesses: ids pasted into config, a silent fallback to one Prague district, and
preferred neighbourhoods matched as free text, which missed every name spelled
with diacritics.

## Decision

**A place is an official RÚIAN territorial unit, identified by its kind and
its code.** Seven kinds are modelled: kraj, okres, obec, obvod, mestska_cast,
cast_obce and ulice, described in `docs/places.md`. RÚIAN codes are stable
across renames and never reused, but unique only within one kind, so the kind
is part of the identity. Names are looked up, never stored as identity.

**The gazetteer holds the places.** It ships with the app, built from the
state address registry, one table per kind keyed by code. Strict containment
is a foreign key. Overlaps, such as a část obce crossing two Prague obvody,
are link tables computed from address points, since every address belongs to
exactly one unit of each kind. It needs no network.

**Search places.** A profile names its search place by kind and code.
The gazetteer's portal tables map each searchable place (every kraj, okres
and Praha obvod) to each portal's own id for it. The gazetteer build harvests
the ids from the portals, joins each to its official place by name and
verifies the result. The tables are never hand-edited. Each scraper resolves
the place at construction and narrows the row to its own frozen view,
keeping no other portal's data. An unknown place fails loudly.

**Listing places.** Each scraper parses its portal's location text into a
`ParsedPlace`, with the names deliberately unlabeled, since a name's kind is
discovered by lookup and never assumed. The one label is an okres the portal
states, since an okres shares its name with its capital town. A pipeline
stage before dedup locates each listing from its text alone, finding the unit
of each kind the text names, with the larger units containing the most
specific one filled in. A GPS point never stands in for a place the text does
not name.
The property keeps the most detailed location any of its postings gave, as a
code per kind plus the house numbers as written. When a place cannot be
trusted it stays unknown. The gazetteer refuses rather than guesses.
[docs/locating.md](../locating.md) walks through the whole path.

## Consequences

- A search, a preference and a listing all speak the same place language, so
  "is this listing in my preferred place" is a comparison of codes.
- A renamed street or a rebuilt gazetteer leaves every stored reference valid.
- The user database refers to the gazetteer by code across two files, which
  no foreign key can check. A code the gazetteer no longer holds reads back as
  unknown.
- Adding a searchable place is a table refresh, not reconnaissance in a
  portal's network tab, and portal knowledge stays in each adapter.
- Dedup never locates. It reads the location the pipeline stage attached.
- Rejected: identifying places by name or slug, which breaks on diacritics,
  renames and repeated names. A nested per-portal payload behind an opaque
  resolver, which would drop typing to dictionary keys mid-chain. Injecting
  the resolved place into each scraper's constructor, which would let the
  criteria and their place disagree.
