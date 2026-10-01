# 5. The desktop app is a Tauri shell over a Python sidecar

Status: accepted (2026-07), recorded 2026-10-01, gate provisionally passed 2026-10-01

## Context

The app is for non-technical users on Windows, macOS and Linux, while the
engine is Python. Scrapers rot whenever a portal changes, so a fix must reach
users without them doing anything, which makes a signed auto-updater the
deciding requirement. The app also needs a tray icon, autostart and native
notifications, and must keep watching with its window closed. The candidates
were a Tauri shell over the Python engine, a local web app opened in the
default browser with a Python tray icon, and a Python-native toolkit such as
Flet or PySide.

## Decision

The desktop app has three parts:

- A Rust shell on Tauri v2, which owns everything the OS provides: the
  window, tray, autostart, notifications and the signed updater. It starts
  the engine, supervises it and stops it.
- The engine, frozen with PyInstaller into a sidecar that needs no Python
  installed. It serves its HTTP API on the loopback interface only.
- The panel, a static SvelteKit build in the OS's own webview, which talks to
  the sidecar's API.

The engine stays fully unaware of the GUI. Notifications default to native OS
notifications, and email becomes an optional channel. Maps use Leaflet with
OpenStreetMap tiles, so no API key or billing account is ever needed.

The decision carries a binding gate. The first milestone runs the bare shell
and sidecar with real data on all three operating systems. If spawning or
packaging the sidecar proves unworkable on any of them, the app falls back to
the local web app design: the same API and the same panel assets in the
default browser, with a Python tray icon. Only the Rust shell is lost in that
fallback.

## Consequences

- Fixes reach users through Tauri's signed updater, which neither rejected
  alternative offered.
- The OS webview keeps the app small, but the panel renders on three
  different engines: WebView2, WebKit and WebKitGTK.
- The project maintains three languages and two build chains: uv with
  PyInstaller, and Cargo with npm.
- Freezing cannot cross-compile, so every OS builds its own installers on its
  own CI runner.
- Signing costs money on macOS and Windows, so shipping signed or unsigned
  with install friction is an open choice for the release.
- Rejected: the local web app as the primary design, because self-updating it
  would be bespoke. Flet and PySide, for having no updater and no reusable
  web UI.

## Gate outcome (2026-10-01)

The gate is provisionally passed, and the Tauri design stands.

- The app builds and packages on Linux, Windows and macOS in CI, one runner
  per OS, with the shell outside the panel's folder.
- On Linux the gate passed in full: the installed app starts the frozen
  engine, shows the inbox, and the engine dies with the shell.
- The build workflow's smoke tests start each OS's frozen engine the way the
  shell does and check its port, token, config and exit on closed stdin.
  They run on every release tag.
- Installing the real app on Windows and macOS waits for testers, once the
  app is usable enough to hand out. Until then the fallback above stays
  available.
