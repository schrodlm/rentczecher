# rentczecher

Multi-profile Czech real-estate watchdog: scrapes portals, deduplicates
listings across them, scores against per-profile preferences, and tracks
what's new for the panel and notification channels to show.

## Language

**Listing**:
One portal's posting, identified as `source:source_id`. The unit scrapers
produce.
_Avoid_: advert, offer, item

**Property**:
The inferred real-world housing unit behind one or more listings. The same
flat posted on two portals is one property with two listings.
_Avoid_: estate, home

**Tracked property**:
A property as one profile tracks it: the listings of it that profile's scans
found, when the profile first saw it, whether it viewed or starred it, and
the lowest current price among those listings. Listings of the property that
the profile's scans never found are not part of it. What the engine serves for
the panel and notification channels to present each in their own way, so each
flat appears once. In the panel every property is a tracked one, so its code
says `Property…` for short.
_Avoid_: tracked listing, inbox card, card

**Inbox**:
The panel's view of one profile's tracked properties, a list beside the
selected one's details. A view of the panel's, never an engine concept. On
screen each is an "inzerát".
_Avoid_: feed

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
One person's saved search: its criteria, its preferences and the portals it
scans. Every scan is per-profile. It keeps every flat its scans found as its
tracked properties, and shows what is new and what has changed.
_Avoid_: search, watch, subscription

**Criteria**:
What a listing must satisfy to be shown for a profile: the search place,
rent or sale, the type of property, the price and size ranges, the minimum
land and the dispositions accepted, none meaning any. A listing failing one is
never shown. When the search place is smaller than the area the portals
search, a listing that cannot be confirmed inside it fails it. A missing size,
land or disposition does not fail a bound, since the portal simply did not say. An atypical disposition is accepted only when named.
_Avoid_: filters, search parameters

**Search place**:
The one place a profile's criteria require a listing to lie in. It may be any
place, from a kraj down to a street.
_Avoid_: location, area, region

**Preference**:
One weighted preferred value that raises a listing's score: a preferred
price, size, land area, disposition or place. Preferences order the listings
that meet the criteria and never hide one.
_Avoid_: wish, scoring setting, weight

**Score**:
How well a listing meets its profile's preferences, worked out by each client
that presents listings. The engine stores preferences and never scores.
_Avoid_: rating, rank

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
The user selected the tracked property in the GUI, opened it, marked it a
favourite, or marked all viewed. A tracked property is viewed once any of its
listings is, so a portal newly posting a viewed flat does not make it new
again. Viewing is never undone.
_Avoid_: seen, read

**New**:
A tracked property observed but not yet viewed. What the GUI's inbox counts
and what the watchdog exists to surface.
_Avoid_: unseen, unread, fresh

**Notified**:
A notification channel delivered the tracked property. A channel is a client
of the API and keeps that record itself, the engine never tracks it.
Notifying does not make a tracked property stop being new, only viewing does.
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
A tracked property the user marked to keep, per profile. Marking it views it.
A favourite and its price history are never pruned, and the GUI shows
favourites apart from the new and viewed ones.
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

**User config**:
The choices a person makes about the app itself on one machine: its theme,
the system's, light or dark, and its language. Kept by the desktop app, never
by the engine, so each client of a headless engine keeps its own. Missing
until the welcome wizard is finished.
_Avoid_: settings, preferences (a profile's scoring), config

**Welcome wizard**:
The three steps the app shows over its dimmed window on the first run: the
language, the theme, and the first profile. Finishing it, with or without a
profile, keeps the user config, so it never shows again.
_Avoid_: onboarding, setup

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
