# Running the engine without the app

The desktop app carries the engine inside it. The engine also runs on its own,
as the `rentczecher` command, for scans from a schedule or a machine without a
screen. It reads and writes the same database as the app.

## Install

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). From the
repository root:

```bash
python3 scripts/bootstrap.py
```

The command is then `engine/.venv/bin/rentczecher`.

## Commands

```bash
rentczecher                          # scan every profile that is not paused
rentczecher --profile <profile id>   # scan one profile, by its id
rentczecher --dry-run                # scan and log the counts, write nothing
rentczecher db migrate               # create or upgrade the database, without scanning
```

Every run applies pending database migrations first, so `db migrate` is rarely
needed. The command only scans. Scoring belongs to the app, so the engine on
its own does not rank listings.

## Scheduled scans

The app scans when you press **Run scan**. For scans on a schedule, add a cron
entry yourself, for example every two hours at a minute of your own:

```cron
17 */2 * * * /path/to/rentczecher/engine/.venv/bin/rentczecher >> ~/.local/share/rentczecher/cron.log 2>&1
```

A run that finds another one still going exits straight away.

## Where the data lives

| | Path |
|---|---|
| The database | `~/.local/share/rentczecher/rentczecher.db` |
| The run lock | `~/.local/share/rentczecher/watchdog.pid` |

`XDG_DATA_HOME` moves the folder as usual, and `RENTCZECHER_DATA_DIR` puts it
anywhere. A checkout whose `engine/data/` already holds `rentczecher.db` uses
that folder instead.

## Profiles

Profiles live in the database. The app's editor creates and changes them
through the engine's API, `/v1/profiles`, whose full contract is
[docs/api/openapi.json](api/openapi.json). Each profile has three parts:

- **Criteria** decide whether a listing is shown: rent or sale, the type of
  property, the search place, the price and size ranges, the minimum land and
  the accepted layouts. They are fixed once the profile is created, since the
  listings it already follows were found under them.
- **Portals** are the sites it scans.
- **Preferences** only order what is shown. Each has a weight, and most have a
  preferred value, such as a preferred price or preferred places.
