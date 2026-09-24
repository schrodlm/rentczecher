# gui

The panel: the SvelteKit web app the desktop shell renders in its webview.
Talks to the sidecar API over HTTP, never to the database or the scrapers
directly.

## Setup

```sh
python3 ../scripts/bootstrap.py
```

Bootstrap installs both environments and creates `.env` from the example.
`.env` sets `PUBLIC_SIDECAR_BASE_URL` (where the sidecar listens) and
`PUBLIC_SIDECAR_TOKEN` (its bearer token). dev.py starts the sidecar with
the same values, so the two sides always agree.

## Developing

```sh
python3 ../scripts/dev.py   # the sidecar and this panel together, one Ctrl-C
npm run dev                 # panel alone, when a sidecar is already running
```

## Locales

User-facing strings live in `locales/*.po`, one catalog per language. `npm
run dev`, `npm run build`, and `npm run check` all run `build:locales` first,
which compiles the `.po` files into the JSON catalogs the app loads at
runtime. Never hand-edit the generated JSON under `src/lib/i18n/`, edit the
`.po` files instead and let the build regenerate it. After adding new `t()`
or `tn()` call sites, `npm run extract:locales` scaffolds the missing
entries to fill in, and the commit gate refuses untranslated msgids.

## API types

`src/lib/api/types.gen.ts` is generated from the sidecar's OpenAPI schema
and is not committed, every build entry point regenerates it.
After a route or schema change on the Python side, regenerate the schema and
the types:

```sh
uv run python scripts/export_openapi_schema.py
npm run generate:api-types
```

## Building

```sh
npm run build
```

`npm run check` runs the Svelte and TypeScript checks the same way CI does.

## Testing

```sh
npm run test
```

Component tests use Vitest and `@testing-library/svelte` against jsdom.
