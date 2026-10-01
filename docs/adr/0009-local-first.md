# 9. Local-first: no accounts, no cloud, no mobile

Status: accepted (2026-09-15), recorded 2026-10-01

## Context

The project is free and open source, kept by one maintainer whose attention,
not implementation time, is the scarce resource. Its users are people
searching for a home, whose searches and history are personal. A hosted
platform publishing market statistics was planned and parked as not viable.
A mobile app was considered, which would have needed a sync service between
phone and computer.

## Decision

The app is local-first. It runs on the user's machine, with no account, no
registration, no subscription, no payment and no cloud service. Searches,
history and settings stay in local files. The only network traffic is the
scraping itself, the map tiles, and the update check.

Mobile is dropped, not deferred: a thin cloud relay for syncing was rejected
because it breaks the local-first value. Remote access comes through headless
mode instead, with the engine on a machine the user owns and clients
connecting to its API.

Nothing built may depend on a hosted platform arriving.

## Consequences

- No server to run, pay for or secure, and no personal data held by the
  maintainer.
- Scraping stays per user, on the user's own connection and for their own
  searches, which is the low-risk legal posture. The app never republishes
  listings.
- No phone app. A user away from their computer relies on email or on a
  headless engine they host.
- Boring technology wins ties: every new operational duty costs the scarce
  attention.
