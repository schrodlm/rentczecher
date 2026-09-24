#!/usr/bin/env python3
"""Writes the sidecar API's OpenAPI schema to docs/api/openapi.json, the
source the GUI's generated TypeScript types build from.

Run: uv run python scripts/export_openapi_schema.py
--check rewrites nothing and exits nonzero when the committed schema is
stale against the code, so the commit gate can enforce regeneration.
"""

import json
import sys
from pathlib import Path

from pydantic.json_schema import models_json_schema

from rentczecher.adapters.api.app import create_app
from rentczecher.adapters.api.deps import ApiDeps
from rentczecher.adapters.api.events import EVENT_PAYLOADS
from rentczecher.adapters.scrapers import scraper_registry

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "api" / "openapi.json"


def build_schema_text() -> str:
    # Schema generation only introspects routes. The app never opens this
    # path, since no request is served.
    unused_db_path = Path("unused.db")
    api_deps = ApiDeps(config={"profiles": {}}, db_path=unused_db_path, scrapers=scraper_registry())
    app = create_app(token="schema-export", api_deps=api_deps)
    schema = app.openapi()
    # SSE payloads ride inside the event stream, never on a route, so the
    # route walk above misses them. Folded into components so the TS
    # generator emits their types like any other model's.
    _, event_defs = models_json_schema(
        [(model, "serialization") for model in EVENT_PAYLOADS.values()],
        ref_template="#/components/schemas/{model}",
    )
    schema["components"]["schemas"].update(event_defs["$defs"])
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> None:
    schema_text = build_schema_text()
    if "--check" in sys.argv:
        committed = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if committed != schema_text:
            sys.exit(
                "docs/api/openapi.json is stale against the code, run: "
                "uv run python scripts/export_openapi_schema.py")
        print("docs/api/openapi.json matches the code.")
        return
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(schema_text)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
