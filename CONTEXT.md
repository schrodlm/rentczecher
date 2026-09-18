# rentczecher

Multi-profile Czech real-estate watchdog: scrapes portals, deduplicates
listings across them, scores against per-profile preferences, and emails
what's new.

## Language

**Listing**:
One portal's posting, identified as `source:source_id`. The unit scrapers
produce and emails show.
_Avoid_: advert, offer, item

**Property**:
The inferred real-world housing unit behind one or more listings. The same
flat posted on two portals is one property with two listings.
_Avoid_: estate, home

**Profile**:
One person's saved search: portals, filters, scoring weights, recipients.
Every pipeline run is per-profile.
_Avoid_: search, watch, subscription

**Seen entry**:
The per-profile record that a listing was observed: first/last seen, last
price, miss count.
_Avoid_: history record

**Active**:
A listing present in the profile's most recent scrape. A listing missing
from one scrape stops being active but is not yet disappeared.
_Avoid_: live, current

**Observed**:
A scrape returned the listing in a run. Says nothing about whether any
person knows it exists.
_Avoid_: seen, found

**Viewed**:
The listing has been on the user's screen in the GUI - scrolling past it
counts; it does not need to be opened.
_Avoid_: seen, read, opened

**New**:
Observed but not yet viewed. What the GUI's inbox counts and what the
watchdog exists to surface.
_Avoid_: unseen, unread, fresh

**Notified**:
A notification channel (email today, others later) delivered the listing.
Channels are toggleable; notifying does not make a listing stop being new -
only viewing does.
_Avoid_: sent, emailed

**Disappeared**:
A listing missed by three consecutive scrapes. Three misses distinguish
real delisting from portal flicker.
_Avoid_: deleted, removed, delisted

**Match**:
A cross-source listing pair the matcher is confident is one property. The
pair merges.
_Avoid_: duplicate

**Uncertain pair**:
A cross-source pair that is plausibly one property but unproven. Recorded,
never merged.
_Avoid_: fuzzy match, low-confidence match

**Favourite**:
A listing the user marked to keep. A favourite and its price history are
never pruned.
_Avoid_: starred, saved, bookmarked

**Cutover**:
The one-time import of JSON seen-state into SQLite, after which the
pipeline reads and writes only SQLite.
_Avoid_: migration (that word is reserved for schema migrations)
