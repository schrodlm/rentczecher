# Panel architecture

The panel is rentczecher's interface: a SvelteKit app built to static files
and shown in the shell's webview. It holds no data of its own. Everything it
shows comes from the engine's API, and everything the user changes goes back
through it. How the panel fits next to the shell and the engine is in
[docs/architecture.md](../docs/architecture.md).

## Shape

- **One page.** `src/routes/+page.svelte` is the whole app: the profile tabs,
  the inbox, the detail and the editor as an overlay. There is no routing
  between screens.
- **No server side.** `ssr = false` and `adapter-static` with an `index.html`
  fallback, so the build is plain files the shell loads.
- **Svelte 5 runes** for state. Shared state that outlives a component lives
  in `*.svelte.ts` classes, such as the profile draft, the run progress and the
  map navigation.

## Starting up

`src/routes/+layout.ts` runs before the first paint:

1. It reads the user config (language and theme) through the shell. Without
   one, this is a first run, and the app follows the system until the welcome
   wizard is done.
2. It applies the theme, so the app never flashes the other one.
3. It loads the translator for the language.

The page then asks the shell for the engine's address and token
(`lib/api/connection.ts`) and starts loading profiles.

## Talking to the engine

| Module | Job |
|---|---|
| `lib/api/types.gen.ts` | Types generated from `docs/api/openapi.json`. Never edited by hand. |
| `lib/api/client.ts` | The API client, `openapi-fetch` over those types, with the token on every request. A refused request becomes an `ApiError` carrying the engine's reason. |
| `lib/api/connection.ts` | Where the engine listens and its token, from the shell's `sidecar_connection` command. |
| `lib/api/events.ts`, `lib/stores/run-progress.svelte.ts` | The server-sent event stream, and a profile's scan as it runs: started, each portal done, finished. |
| `lib/api/engine.ts` | Notice from the shell that the engine stopped. |

Because the types are generated, an API change the panel has not followed
fails `npm run check`. `npm run codegen` regenerates them, and the dev and
build scripts run it first.

## The parts of the interface

| Folder | What is in it |
|---|---|
| `lib/components/` | The inbox and its rows, the header with the scan button, sort and filter menus, the property detail, the price chart, the score ring, the theme and language switches |
| `lib/editor/` | The profile editor and `ProfileDraft`, the editor's state, which turns a stored profile into editable form and back into an API body |
| `lib/forms/` | Inputs the editor is built from: portal tiles, layout chips, range and value sliders, preferred places |
| `lib/map/` | The map of Czechia, built from the gazetteer by `scripts/czech_map.py`, the search-place picker and the small place map in the detail |
| `lib/scoring/` | Scoring: the score itself, the preferences, and the editor section where weights are split by dragging |
| `lib/welcome/` | The first-run wizard: language, theme, and a short tour |
| `lib/i18n/` | Translation |
| `lib/styles/` | Design tokens and global styles |

The inbox's sorting, filtering and the facts shown for a listing are plain
functions in `lib/property-*.ts`, apart from the components that draw them, so
they are tested without rendering.

## Scoring

The engine stores each profile's preferences and never scores. The panel
works the score out when it shows a listing (`lib/scoring/score.ts`): each
preference with a weight gives the listing points out of that weight, and the
editor keeps the weights adding up to 100. The detail shows the points each
preference gave. Scores pinned in `recorded-scores.json` keep the formula
from drifting.

## Translation

English is the source language, written literally at every call site as
`t.t('…')` or `t.tn(…)` for plurals. `locales/cs.po` holds the Czech, and
`npm run build:locales` compiles it to `lib/i18n/cs.json`, which is generated
and not committed. A missing entry falls back to the English text.

`npm run check:locales` fails when the catalog and the source disagree, and the
commit hooks run it. The scan only sees string literals, so a message is never
built at runtime.

## The user config

The language and theme belong to this machine, not to the engine, since a
headless engine could serve several devices. The shell keeps them in a small
file in the operating system's config folder, and the panel reads and writes
it through the shell's commands (`lib/user-config.ts`). Choosing a language
reloads the app, which reopens on the same profile and listing.

## Tests

Vitest with Testing Library, next to the code they test (`*.test.ts`).
Components that need a binding or a context are rendered through small
harnesses in `lib/test-support/`, and `renderWithTranslator` renders in Czech,
so a missing translation shows up. Run them with `npm test`, and the type check
with `npm run check`.
