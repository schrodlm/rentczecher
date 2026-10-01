# 4. The engine is one package, and every interface is its client

Status: accepted (2026-07), recorded 2026-10-01

## Context

The project began as a pile of flat scripts run by cron. It needed to grow a
desktop app, keep a command line for power users, and leave room for remote
clients later, without a rewrite for each. The candidates were a modular
monolith package, a long-running local service that interfaces connect to,
and a library built around an event bus.

## Decision

The engine is one installable Python package, `rentczecher_engine`, in light
hexagonal layers:

- `domain/` holds frozen dataclasses and no I/O.
- `services/` holds the pipeline use cases. They depend only on Protocols
  (`Scraper`, `RunStore`, `Notifier`), never on a concrete adapter.
- `adapters/` holds everything that touches the outside world: scrapers,
  SQLite repositories, notifiers, config, and the HTTP API.
- `cli/` parses arguments and orchestrates, and owns no logic.

Every interface is a client of the same services. The command line calls them
directly. The desktop app reaches them through the sidecar's API, which is one
more adapter. No interface reimplements domain logic.

Storage is SQLite, embedded through the standard library, one file on the
user's disk. The schema evolves through numbered SQL migrations tracked by
`PRAGMA user_version`, with no ORM and no migration framework.

The engine installs no system service. It runs while something runs it: a
command-line invocation, or the desktop app, which is the always-running
process when background watching needs one.

## Consequences

- One codebase and one test suite serve every interface, so a fix reaches the
  command line and the app at once.
- Services are tested with in-memory fakes of their Protocols, with no
  network or disk.
- A second storage backend or notification channel is a new adapter, not a
  change to services.
- Nothing to install, start or uninstall at the OS level, on any platform.
- Hand-written SQL is more lines than an ORM, in exchange for queries a reader
  can see and a schema that fails loudly when it drifts.
- Rejected: a local service daemon, for its operational burden across three
  operating systems before anything needed it. An event-bus-first design, for
  adding a second mental model before a second subscriber existed.
