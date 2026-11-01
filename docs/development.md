# Building and maintaining

Setup and the everyday workflow are in [CONTRIBUTING.md](../CONTRIBUTING.md).
This page covers building the installers and refreshing the data the engine
ships.

## Building the desktop app

```bash
(cd panel && npm run tauri build)                  # every installer format for this OS
(cd panel && npm run tauri build -- --bundles deb) # only the .deb on Linux
```

One command builds the panel, freezes the engine into the sidecar and
compiles the shell. The installers land in `shell/target/release/bundle/`.
Each OS builds only its own installers, since the frozen engine cannot be
cross-compiled.

To freeze the engine alone, for example to run the smoke tests:

```bash
(cd engine && uv run python scripts/freeze_sidecar.py)
(cd engine && uv run pytest -m smoke)
```

## Release builds

A release build also bundles the license and the third-party notices, which
list every package inside the app with its license text:

```bash
cargo install --locked --features cli cargo-about   # once, lists the Rust crates
(cd panel && npm run tauri build -- --config ../shell/tauri.release.conf.json)
```

`shell/tauri.release.conf.json` is laid over `tauri.conf.json` and replaces its
build command and bundled files whole, so a change to either belongs in both.
The build fails when a bundled package uses a license missing from the
`accepted` list in `shell/about.toml`.

CI builds the installers this way for every `v*` tag, and for every push to
the `build-test` branch, which is how a release build is tried without
tagging.

## The gazetteer

Places come from the gazetteer, a SQLite file shipped with the engine
(`engine/src/rentczecher_engine/adapters/geocoding/gazetteer.sqlite`). It holds
every official Czech place from the RÚIAN address registry, keyed by its RÚIAN
code, and the ids the portals search those places by, for the portals that
do not search by RÚIAN code.
[places.md](places.md) describes the units, and [locating.md](locating.md) how
a listing's location text becomes them.

It is built, never edited by hand. Rebuild it when ČÚZK publishes a registry
dump worth picking up, or when a portal renumbers its places. The sign of the
latter is a place that used to return listings suddenly returning none, or the
`live` search-place tests failing:

```bash
(cd engine && uv run python -m scripts.gazetteer build)
```

The build downloads the registry, reads each portal's list of searchable
places, joins every portal place to its official one by name, and verifies the
result. It takes about a minute and needs the portals reachable. Only a fully
verified file replaces the shipped one.
[engine/scripts/gazetteer/README.md](../engine/scripts/gazetteer/README.md) has
the details.

## Adding a portal

A portal is first checked for what it asks of apps, in its terms and its
robots.txt, and for whether it answers the app's own User-Agent, under the
rules of [ADR 12](adr/0012-one-private-copy-per-person.md). Then these places
learn its name:

- its adapter in `engine/src/rentczecher_engine/adapters/scrapers/`,
  registered in `ALL_SCRAPERS`, and in `ADVERT_GALLERY_PARSERS` when its
  results show only one photo
- the `Portal` type in `domain/profile.py` and a migration adding its row to
  the `portals` table
- its search area: a portal table in the gazetteer, harvested by the build,
  unless it names places by their RÚIAN codes
- `docs/api/openapi.json`, regenerated with
  `uv run python scripts/export_openapi_schema.py` in `engine/`
- the panel's `PORTALS` in `panel/src/lib/portals.ts`, with its icon and, for
  a portal that asks apps not to read it, the link to its terms
- a page in [portals/](portals/), the table in
  [using-the-portals.md](using-the-portals.md), and the site's portal list
