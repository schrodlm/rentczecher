# 12. One private copy per person

Status: accepted (2026-10-15). Amends ADR 10 on where channels deliver.

## Context

The app reads listings from portals that never agreed to it. What keeps that
defensible is the shape of the use: one person, on their own computer, reading
the portals for their own home search and going back to the portal to act on
what they find. The same code turns into something else when it serves many
people from one place, keeps what it read long after the search needed it,
passes listings on to others, or keeps asking a portal that has said no.

ADR 9 already rules out a hosted service. This record states the rest as rules
every feature is checked against, so the shape survives features nobody has
planned yet.

## Decision

- **One owner per engine.** An engine serves one person and their own devices.
  There are no accounts, roles or share links, and the project runs no hosted
  instance. The engine binds to loopback. A headless engine binds only to
  private or overlay addresses, behind TLS, never a public interface.
- **Listing content stays on the owner's machine.** The project ships no
  export of listing data, no public API, no sync and no shared cache. A
  notification channel delivers only to the owner's own private endpoints, as
  links plus a few facts (price, size, place, a price drop), never a portal's
  photos or text.
- **The store is a working set, not an archive.** A listing and everything
  read with it (its property, prices, places and photos) is deleted once no
  profile has tracked it for the retention horizon. Favourites are the only
  lasting exception. Deleting a profile deletes what only it held.
- **A refusal is a no.** The app names itself honestly in every request. It
  never uses proxies, rotating identities, or CAPTCHA or firewall bypass. A
  portal that refuses the app is left alone until it allows it again, and a
  portal that refuses a plain client is not added. Scans keep a minimum
  interval and pause between requests.
- **A portal that asks not to be read is off by default.** When a portal's
  terms or `robots.txt` ask automated clients to stay away, the user turns it
  on in their profile after being told so.
- **The user goes back to the portal.** Every listing links prominently to its
  posting and names its source. The app never stores or shows a portal's
  description text. A portal's name and icon appear only to say where a
  listing came from, and an icon goes at its owner's first objection. The app
  is never presented as a replacement for a portal or its paid services.
- **No money tied to features.** No paid tier, ads or gated features. A
  donation link, if there is one, is an unconditional thank-you.

## Consequences

- Each install costs a portal no more than one person searching by hand,
  which is the case the law is kindest to.
- Features that cross a rule are rejected outright, not built behind a flag:
  a shared engine, a public channel, a bulk export, a statistics service.
- Old listings disappear unless starred, so the app cannot answer questions
  about the market's past, only about the user's own search.
- Rejected: a policy left to each user's judgement, which makes the maintainer
  the author of every misuse the code makes easy.
