rentczecher is two programs. The engine is Python: it scrapes the portals, matches flats and keeps everything in SQLite. The desktop app is a Tauri shell written in Rust, which shows the SvelteKit panel in a webview and starts the engine as a sidecar process. For a while the window could already show the inbox, but only on my machine, with Python installed and everything started by hand. This step closed that gap.

## One package, no Python

A release build now starts a self-contained engine frozen with PyInstaller, shipped as a resource inside the app bundle, so nothing else needs to be installed. A `.deb` package built, and when I unpacked it, it ran and showed the inbox.

Unpacking it was a lesson of its own. A `.deb` is a plain `ar` archive of three members: a version marker, the control files and the payload. Looking inside shows exactly what the installer would put where. The app itself is a single binary with the panel embedded at build time, and the frozen engine sits next to it as a folder of resources.

## Neither half dies alone

Two processes can fail in two directions, so both are covered.

<figure>
<svg viewBox="0 0 640 262" role="img" aria-label="The desktop app and the engine side by side. The app holds the engine's stdin open, reads its stdout, and the panel talks to the engine over an HTTP API on localhost.">
<defs><marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" style="fill: var(--muted)"/></marker></defs>
<rect x="20" y="20" width="200" height="222" rx="12" style="fill: var(--surface); stroke: var(--olive); stroke-width: 2"/>
<text x="40" y="50" style="fill: var(--text); font: 700 16px system-ui, sans-serif">Desktop app</text>
<text x="40" y="70" style="fill: var(--muted); font: 13px system-ui, sans-serif">Tauri, Rust</text>
<rect x="40" y="166" width="160" height="62" rx="8" style="fill: var(--bg); stroke: var(--line-strong); stroke-width: 1.5"/>
<text x="56" y="192" style="fill: var(--text); font: 700 14px system-ui, sans-serif">Panel</text>
<text x="56" y="212" style="fill: var(--muted); font: 13px system-ui, sans-serif">SvelteKit, webview</text>
<rect x="420" y="20" width="200" height="222" rx="12" style="fill: var(--surface); stroke: var(--amber); stroke-width: 2"/>
<text x="440" y="50" style="fill: var(--text); font: 700 16px system-ui, sans-serif">Engine</text>
<text x="440" y="70" style="fill: var(--muted); font: 13px system-ui, sans-serif">Python, PyInstaller</text>
<text x="440" y="170" style="fill: var(--text); font: 13px system-ui, sans-serif">checks the portals</text>
<text x="440" y="192" style="fill: var(--text); font: 13px system-ui, sans-serif">matches flats</text>
<text x="440" y="214" style="fill: var(--text); font: 13px system-ui, sans-serif">remembers what you saw</text>
<line x1="222" y1="88" x2="416" y2="88" marker-end="url(#arrowhead)" style="stroke: var(--muted); stroke-width: 2"/>
<text x="320" y="80" text-anchor="middle" style="fill: var(--text); font: 700 13px system-ui, sans-serif">stdin, held open</text>
<text x="320" y="106" text-anchor="middle" style="fill: var(--muted); font: 12px system-ui, sans-serif">closes → engine stops</text>
<line x1="418" y1="146" x2="224" y2="146" marker-end="url(#arrowhead)" style="stroke: var(--muted); stroke-width: 2"/>
<text x="320" y="138" text-anchor="middle" style="fill: var(--text); font: 700 13px system-ui, sans-serif">stdout</text>
<text x="320" y="164" text-anchor="middle" style="fill: var(--muted); font: 12px system-ui, sans-serif">closes → app shows a banner</text>
<line x1="204" y1="204" x2="416" y2="204" marker-start="url(#arrowhead)" marker-end="url(#arrowhead)" style="stroke: var(--muted); stroke-width: 2; stroke-dasharray: 5 4"/>
<text x="320" y="196" text-anchor="middle" style="fill: var(--text); font: 700 13px system-ui, sans-serif">HTTP API, localhost</text>
<text x="320" y="222" text-anchor="middle" style="fill: var(--muted); font: 12px system-ui, sans-serif">REST calls, Server-Sent Events</text>
</svg>
<figcaption>The shell and the engine watch each other through stdin and stdout. The panel talks to the engine over HTTP.</figcaption>
</figure>

If the shell goes away, the engine must not keep running in the background. The shell holds the write end of the engine's stdin and never writes to it. The engine runs with `--exit-with-parent` and watches that pipe. When the shell dies for any reason, even `kill -9`, the OS closes the pipe and the engine shuts itself down. Force-killing the shell stopped the engine in 0.21 seconds.

If the engine dies, the window must not keep pretending. When the engine's stdout closes, the shell emits an event to the panel, which shows a banner, 0.11 seconds after the engine was killed. And if the engine never reports healthy at startup, a native error dialog explains it and the app quits, instead of opening an empty window.

## A Content Security Policy

The panel runs in a webview, so it got a Content Security Policy: an allowlist of what the page may load and connect to, enforced by the webview itself. It is strict in release builds, with a looser dev policy so Vite's live reload keeps working. Tauri's IPC goes through its own internal addresses, so those have to be on the list too.

## Surprises

The release build did not compile at first. The code that starts the engine existed only under `#[cfg(debug_assertions)]`, so the release path had never been compiled. The checks now build both profiles. And AppImage would not build on my machine, because a desktop integration tool I have installed intercepts every AppImage, including the build tools themselves. The `.deb` builds fine locally, so AppImage moved to the CI runners.
