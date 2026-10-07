"""The panel's map of Czechia offers places by their gazetteer codes, so it
must be drawn from the gazetteer the engine ships."""

import json
from pathlib import Path

import pytest

from rentczecher_engine.adapters.geocoding.gazetteer import open_gazetteer

MAP = Path(__file__).resolve().parents[2] / "panel" / "src" / "lib" / "map" / "czech-map.json"
REDRAW = "redraw it with `uv run scripts/czech_map.py` inside panel/"


@pytest.fixture(scope="module")
def drawn() -> dict:
    return json.loads(MAP.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gazetteer():
    conn = open_gazetteer()
    yield conn
    conn.close()


def test_the_map_was_drawn_from_the_shipped_gazetteer(drawn, gazetteer):
    stmt = "SELECT key, value FROM meta WHERE key IN ('generated_at', 'source')"
    shipped = {row["key"]: row["value"] for row in gazetteer.execute(stmt)}
    assert drawn["gazetteer"] == shipped, f"the map was drawn from another gazetteer build, {REDRAW}"


@pytest.mark.parametrize(("layer", "table"), [("kraje", "kraje"), ("obvody", "obvody"), ("obce", "obce")])
def test_every_place_the_map_offers_is_in_the_gazetteer(drawn, gazetteer, layer, table):
    codes = {row["code"] for row in gazetteer.execute(f"SELECT code FROM {table}")}
    missing = [place["name"] for place in drawn[layer] if place["code"] not in codes]
    assert missing == [], f"the map offers {table} the gazetteer no longer knows: {missing}, {REDRAW}"


def test_every_district_the_map_offers_is_in_the_gazetteer(drawn, gazetteer):
    okresy = {row["code"] for row in gazetteer.execute("SELECT code FROM okresy")}
    obce = {row["code"] for row in gazetteer.execute("SELECT code FROM obce")}
    missing = [district["name"] for district in drawn["okresy"]
               if district["code"] not in (okresy if district["kind"] == "okres" else obce)]
    assert missing == [], f"the map offers districts the gazetteer no longer knows: {missing}, {REDRAW}"
