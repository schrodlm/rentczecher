# 10. Notification channels are API clients

Status: accepted (2026-10-04). Supersedes the "notify, then commit" rule of
ADR 7.

## Context

The engine used to send the email itself, in Czech, to recipients set per
profile, and it committed a scan only after that email went out. That tied
the engine to one channel, one language and one delivery's success. Every
channel added later, and every language, would have grown inside the engine,
and a mail server being down would hold back the record of what was scanned.

## Decision

The engine scans, dedups, scores and tracks what is new, viewed and
favourited, and exposes all of it through its API and its event stream. It
knows nothing about email, recipients or languages.

- **A notification channel is a client of the API,** like the panel. Email is
  the first, as a separate small program or part of the shell.
- **A scan always commits.** A channel keeps its own record of what it
  delivered and asks the engine for what arrived since. A failed delivery is
  retried by the channel, and nothing in the engine is wrong.
- **A channel's wording lives with it,** translated like the panel.

## Consequences

- The engine's scan state is never held back by a delivery, so the panel and
  every channel see the same listings at once.
- Delivery bookkeeping moves out of the engine with the channel. Its
  notification table goes.
- Scans are quiet until the first channel exists. The panel still shows
  everything that is new.
- Rejected: keeping email in the engine behind a channel interface, which
  keeps the engine owning recipients, languages and delivery state.
