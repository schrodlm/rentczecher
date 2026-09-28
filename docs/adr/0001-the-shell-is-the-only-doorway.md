# 1. The shell is the only doorway to the sidecar

Status: accepted (2026-09-24), revised 2026-09-28

## Context

The panel talks to the sidecar over its loopback API with a bearer token, so
something must tell the panel where the sidecar listens and which token it
expects. In the packaged app the shell spawns the sidecar and holds both. An
earlier version of this decision also gave development a second doorway: a
browser tab fed by public Vite env vars from gui/.env, with dev.py standing in
for the shell. Once the shell starts the engine itself, that doorway only
duplicates it.

## Decision

The shell is the only doorway, in development and in release. Development
happens in the shell's window: `npm run tauri dev`. A debug build of the
shell starts the engine from source with uv, so engine edits show on the next
launch. A release build starts the frozen sidecar. The panel always receives
the base URL and token from the shell's sidecar_connection command.
gui/.env, the PUBLIC_ sidecar variables and dev.py are removed.

## Consequences

- One path from development to release. Development runs on WebKitGTK, one of
  the three engines the app ships on.
- A real token never enters the repo or any file. The shell generates it at
  every launch.
- Panel work needs the Rust toolchain and the platform's webview libraries,
  checked by the bootstrap script. Panel tests still run in jsdom without
  either.
- Debug builds keep a web inspector, and the window still loads from Vite, so
  panel edits hot reload.
- A browser client, if headless mode brings one, is designed fresh with a
  real token pairing flow, not env vars.
