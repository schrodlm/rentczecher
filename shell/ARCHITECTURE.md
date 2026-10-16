# Shell architecture

The shell is rentczecher's desktop window, a Tauri 2 app in Rust. It owns what
the operating system provides, starts the engine and keeps it tied to the
window's life, and hosts the panel in the system's webview. It holds no
listing data and no business logic. How it fits next to the panel and the
engine is in [docs/architecture.md](../docs/architecture.md).

Almost all of it is `src/lib.rs`. `src/main.rs` only calls `run()`.

## Starting

1. **The engine first, the window second.** The window is declared in
   `tauri.conf.json` but created only once the engine answers, so the panel
   never loads before it can reach the engine.
2. **A fresh token.** `generate_token()` takes 32 bytes from the OS random
   source. It lives only in memory, for this launch.
3. **Spawning.** A debug build runs the engine from source with
   `uv run rentczecher serve`. A release build runs the frozen sidecar the
   installer carries in its resources. Both get `--port 0 --exit-with-parent`,
   the window's origins as `--allow-origin`, and the token in
   `RENTCZECHER_API_TOKEN`. On Windows the engine starts without a console
   window of its own.
4. **The port.** A thread reads the engine's output and picks up the
   `PORT=` line. It keeps reading afterwards, since a full pipe would block
   the engine, and logs every other line.
5. **Health.** The shell polls `/v1/health` with the token until it answers.
   A bound port only proves the socket exists, the answer proves the engine is
   serving. The engine gets 10 seconds to announce its port and 10 more to
   answer.
6. **Failure.** If any of this fails, the shell kills a half-started engine,
   shows a plain error dialog in English (the translations load with the
   window, which does not exist yet) and exits once it is dismissed.

## Keeping the engine tied to the window

The shell holds the write end of the engine's stdin and never writes to it.
The engine runs with `--exit-with-parent`, so when the shell ends, however it
ends, the operating system closes that pipe and the engine shuts itself down.
On a normal exit the shell also kills the engine directly.

When the engine's output closes, the engine is gone. The shell then emits the
`engine-stopped` event, and the panel shows that the engine stopped.

## Commands for the panel

| Command | Job |
|---|---|
| `sidecar_connection` | The engine's address and token |
| `read_user_config`, `write_user_config` | The user config file's text. The panel owns its shape, the shell only moves the text. |
| `open_in_browser` | Opens a portal link in the user's browser, since the window opens no windows of its own |

The panel may call only what is allowed in `capabilities/default.json`: these
commands, the core defaults and setting the window's theme.

## Security

- The content security policy in `tauri.conf.json` lets the page load only its
  own files and images, and connect only to the shell's IPC and to
  `127.0.0.1`. The panel can reach no other site.
- The engine listens on loopback only and refuses requests without the token.
- The user config is the only file the panel can touch, and only through the
  shell, which picks the path.

## The user config

`user_config.json` in the operating system's config folder for the app. It
holds what a person chose about the app on this machine, the language and the
theme. A missing file means the welcome wizard has not run yet.

## Development

With `RENTCZECHER_SCENARIO` set, a debug build first replays that scenario into
`rentczecher-scenarios/<name>` in the system's temp folder, then starts the
engine there and keeps the user config there too. Development never touches
the real data. See [CONTRIBUTING.md](../CONTRIBUTING.md#scenarios).

## Building

`tauri.conf.json` drives every build: it runs the panel's build and freezes the
engine before compiling, and bundles the frozen engine as a resource.
`tauri.release.conf.json` is laid over it for releases and adds the license and
the third-party notices. The notices' Rust part comes from `cargo about`,
configured in `about.toml` and laid out by `about.hbs`. See
[docs/development.md](../docs/development.md).
