# 1. Two doorways to the sidecar: dev env vars and shell spawn

Status: accepted (2026-09-24)

## Context

The GUI talks to the sidecar over loopback HTTP with a bearer token. A
packaged desktop app and a developer working on the GUI need different
provisioning: the shell generates a fresh random token at every launch,
while a developer runs the sidecar and the Vite dev server by hand and
works in a browser tab.

## Decision

SidecarClient takes the base URL and token as constructor inputs and never
knows where they come from. The page constructing it owns provisioning. In
dev they come from gui/.env, exposed through Vite's PUBLIC_ env var
convention, with a committed .env.example placeholder. In the packaged app
the shell supplies both at spawn. The dev doorway is permanent, not a
stopgap: GUI development stays in the browser for hot reload and dev tools
even after the shell ships. scripts/dev.py plays the shell's role in dev,
reading gui/.env once and starting the sidecar and the Vite server with
the same token.

## Consequences

- A real token never enters the repo. The committed placeholder guards
  nothing by itself, a token is only valid against a sidecar started with
  the same value.
- The client is constructible against any fake in tests, no environment
  tricks needed.
- Both doorways exercise the same API surface, so dev-mode behavior stays
  representative of the packaged app.
