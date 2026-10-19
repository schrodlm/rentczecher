# 13. Photos are fetched as a person looks

Status: accepted (2026-10-19).

## Context

Photos are what a person remembers of a flat, and a portal's photos vanish
with its advert, so the app keeps its own copy. But a broad first scan can
bring thousands of new listings. Downloading every listing's full gallery
would mean tens of thousands of photos and an advert page opened for every
Bezrealitky and RE/MAX listing, from one install. That is far more than one
person searching by hand, which ADR 12 sets as the limit.

## Decision

The app fetches photos the way a person looks at them.

- **After each scan, each new listing gets its main photo,** the one a
  person scrolling the results sees anyway, within a budget per portal per
  scan. What the budget leaves carries over to the next scan, newest first.
- **A listing's full gallery, at most 20 photos, is fetched when the user
  opens or stars the flat.** That is the user's own act, like opening the
  advert. Where the gallery is not in the search results, the advert's page
  is opened once, then.
- **A refusal stops the pass for that host,** and a photo that keeps failing
  is given up after a few attempts, never retried on every scan.
- **Photos are kept as files exactly as the portal served them,** and live
  as long as their flat: deleted when the retention sweep deletes it, kept
  while it is starred. A sweep deletes any file no listing still refers to.
- **The panel loads them from the engine through signed links,** since an
  image request cannot carry the API's token. A link is valid for the
  engine's run.

## Consequences

- A flat the user never opened keeps only its main photo once its advert
  ends.
- Opening a flat for the first time shows its main photo at once, and the
  rest of the gallery a few seconds later.
- The operator page and the docs say that the app opens an advert's page
  once, when its user opens that flat.
- Rejected: every new listing's full gallery after each scan, which breaks
  ADR 12's limit at any broad search.
