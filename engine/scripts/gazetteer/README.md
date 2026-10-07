# Gazetteer build

Builds `gazetteer.sqlite`, the database of every Czech place the engine ships
with, from RÚIAN (the state address registry, published monthly by ČÚZK) and a
live harvest of the portals. Never hand-edit the file. Rebuild it instead.

```bash
cd engine
uv run python -m scripts.gazetteer build
```

Needs ČÚZK and the portals reachable. Options:

| Option | Use |
|---|---|
| `--state-file PATH` | an already downloaded `ST_UZSZ` zip |
| `--address-dump PATH` | an already downloaded `OB_ADR` zip |
| `--out PATH` | write somewhere else (default: the shipped file) |

Rebuild after changing `schema.sql` or `normalize_name`, bumping
`SCHEMA_VERSION` in `src/rentczecher_engine/adapters/geocoding/gazetteer.py`
first, since the engine refuses a file built for another version. The root
README lists the other reasons to rebuild.

A build that replaces the shipped file also redraws the panel's map of
Czechia from it (`panel/scripts/czech_map.py`), since the map offers places
by their codes. A test fails while the map was drawn from another build.

## What it does

1. **Download** (`sources.py`) the two RÚIAN files: the state file (official
   names, parents, definition points) and the address dump (streets, and which
   units overlap).
2. **Build** (`build.py`, `ruian/`, `database.py`) one table per kind of place
   (kraj down to ulice, see [docs/places.md](../../../docs/places.md)) into a
   temporary file, parents before children.
3. **Harvest** (`harvest.py`, `portals/`) each portal's searchable places and
   join them to the official kraje, okresy and Praha obvody by name. Every
   official place must be mapped by every portal.
4. **Verify** (`verify.py`) row counts, the schema version, the hierarchy,
   that every portal covers every search place, and a few known places.
5. **Ship**: replace the shipped file, only if every step passed.

`__main__.py` runs these steps, `schema.sql` defines the tables and the
`places` view, and `model.py` holds the row types passed between them. How the
engine reads the file is in [docs/locating.md](../../../docs/locating.md).
