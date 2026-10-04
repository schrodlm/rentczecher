# rentczecher

Multi-profile Czech real-estate watchdog: scrapes portals, deduplicates
listings across them, scores against per-profile preferences, and tracks
what's new for the panel and notification channels to show.

## Language

**Listing**:
One portal's posting, identified as `source:source_id`. The unit scrapers
produce and the panel shows.
_Avoid_: advert, offer, item

**Property**:
The inferred real-world housing unit behind one or more listings. The same
flat posted on two portals is one property with two listings.
_Avoid_: estate, home

**Disposition**:
A property's layout: its number of rooms and whether the kitchen is a
kitchenette (2+kk) or a separate room (2+1). A layout fitting neither is
atypical. A garsoniéra is a 1+kk.
_Avoid_: room count

**Disposition text**:
The portal's own words for a listing's layout, kept as written. The
disposition is parsed from it. Text naming no layout, such as a building
type, leaves the disposition unknown.
_Avoid_: disposition

**Place**:
One official territorial unit from RÚIAN, the state register of addresses: a
kraj, okres, obec, obvod, městská část, část obce or ulice. Identified by its
kind and code, never by its name.
_Avoid_: area, region, locality

**Location**:
Where a property lies: the place of each kind its listing's text names, plus
the house numbers as written.
_Avoid_: address

**Location text**:
The portal's own words for where a listing is, kept as written. The location
is resolved from it.
_Avoid_: address, location

**Gazetteer**:
The register of every Czech place, used offline. It turns location text into
a location.
_Avoid_: geocoder, place database

**Profile**:
One person's saved search: portals, filters, scoring weights.
Every scan is per-profile.
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
A scrape returned the listing in a scan. Says nothing about whether any
person knows it exists.
_Avoid_: seen, found

**Viewed**:
The user clicked the listing open from the GUI, or marked all viewed.
_Avoid_: seen, read

**New**:
Observed but not yet viewed. What the GUI's inbox counts and what the
watchdog exists to surface.
_Avoid_: unseen, unread, fresh

**Notified**:
A notification channel delivered the listing. A channel is a client of the
API and keeps that record itself, the engine never tracks it. Notifying does
not make a listing stop being new, only viewing does.
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

**rentczecher**:
The product as a whole: the engine that scrapes and tracks listings, and the
desktop app that puts a face on it, plus the command line for power users.
The engine, panel and shell are its parts.
_Avoid_: using it for the engine alone

**Engine**:
The Python application as a whole: pipeline, storage, scrapers, API. The
sidecar is the engine in its serving role, a command-line invocation is the
same engine in its batch role.
_Avoid_: backend, server, core, rentczecher (the whole product)

**Panel**:
The SvelteKit web application. It renders in the shell's webview and talks
only to the sidecar.
_Avoid_: frontend, webapp, GUI (the whole desktop experience, not this app)

**Shell**:
The desktop program the user launches. It owns the window showing the GUI
and the sidecar's lifetime.
_Avoid_: wrapper, launcher, frontend

**Background watching**:
The engine keeps running scheduled scans after the window is closed, shown by
an icon in the system tray. On by default, and off whenever no tray exists.
_Avoid_: background mode, running in background, minimized

**Close**:
Hiding the window. With background watching on, the engine keeps watching.
_Avoid_: exit, minimize

**Quit**:
Ending the app entirely: the shell and the sidecar both exit, and any running
scan stops.
_Avoid_: close, exit

**Sidecar**:
The Python process the shell spawns at launch. It serves the loopback API,
executes scans, and dies with the shell.
_Avoid_: server, backend, daemon

**Token**:
The random secret the shell generates at every launch and hands the sidecar
at spawn. Every API request must present it back. It is never persisted and
dies with the process.
_Avoid_: API key, credential, session

**Scan**:
One execution of the pipeline for one profile: scrape its portals, dedup,
diff against what it has seen, commit. Scans are queued and execute strictly
one at a time.
_Avoid_: run, job, task, sync

**Scenario**:
A named story of scans for one profile, each scan listing what it saw,
replayed through the engine to set up a known inbox. Development opens the
app on one, and tests start from one.
_Avoid_: fixture (one scenario feeds many fixtures), seed, mock data

**Event**:
A fact the sidecar announces the moment it happens: a scan started, a portal
finished, a scan finished, new listings arrived.
_Avoid_: notification (reserved for listing delivery), message

**Broker**:
The in-process fan-out point. Publishers hand it events and it copies each
one to every current subscriber, knowing nothing about either side.
_Avoid_: bus, router, dispatcher

**Event stream**:
The long-lived HTTP response through which a connected GUI receives events.
One connected GUI is one subscriber on the broker.
_Avoid_: push channel, websocket

**OpenAPI**:
The vendor-neutral JSON format describing an HTTP API's endpoints and
shapes. Ours is generated from the code, committed at docs/api/openapi.json,
and the GUI's TypeScript types are generated from it.
_Avoid_: Swagger (its old name), FastAPI (the framework, not the format)

**FastAPI**:
The Python framework the sidecar's API adapter is built on. It routes
requests to typed functions and generates the OpenAPI document from them.
_Avoid_: OpenAPI (the format, not the framework)

**i18n**:
Internationalization, the industry numeronym (i, then 18 letters, then n).
The concern of a multi-language UI, not a library. The GUI's runtime is our
own code. English msgids written at call sites are the source language and
cs.po derives Czech from them.
_Avoid_: i18next, svelte-i18n (libraries branded after the term)
