#!/usr/bin/env python3
"""Writes the sidecar API's OpenAPI schema to docs/api/openapi.json, the
source the GUI's generated TypeScript types build from.

Run: uv run python scripts/export_openapi_schema.py
"""

import json
from pathlib import Path

from rentczecher.adapters.api.app import create_app
from rentczecher.adapters.api.deps import ApiDeps
from rentczecher.adapters.scrapers import scraper_registry

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "api" / "openapi.json"


def main() -> None:
    # Schema generation only introspects routes. The app never opens this
    # path, since no request is served.
    unused_db_path = Path("unused.db")
    api_deps = ApiDeps(config={"profiles": {}}, db_path=unused_db_path, scrapers=scraper_registry())
    app = create_app(token="schema-export", api_deps=api_deps)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
