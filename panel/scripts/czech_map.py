# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=2", "scipy>=1.13", "contourpy>=1.3"]
# ///
"""Draws the panel's map of Czechia once, from the gazetteer's own points.

Every bit of land goes to the nearest obec (or Praha městská část), and the
outline of each kraj, okres and Praha obvod is traced from that, so borders
are approximate. Each okres keeps its 12 biggest towns, sized by their street
count, which the gazetteer has where it has no population.

Run: uv run scripts/czech_map.py (inside panel/)
"""

import json
import math
from itertools import pairwise
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import contourpy
import numpy as np
from scipy.ndimage import binary_fill_holes, distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree

PANEL = Path(__file__).resolve().parent.parent
GAZETTEER = PANEL.parent / "engine" / "src" / "rentczecher_engine" / "adapters" / "geocoding" / "gazetteer.sqlite"
OUT = PANEL / "src" / "lib" / "map" / "czech-map.json"

LON_WEST, LON_EAST, LAT_SOUTH, LAT_NORTH = 12.0, 18.95, 48.5, 51.1
WIDTH = 900
X_SCALE = math.cos(math.radians(49.8))
HEIGHT = round(WIDTH * (LAT_NORTH - LAT_SOUTH) / ((LON_EAST - LON_WEST) * X_SCALE))
KM_PER_CELL = (LON_EAST - LON_WEST) * X_SCALE * 111.32 / WIDTH
# Land farther than this from any village is outside the country.
MAX_KM_FROM_A_VILLAGE = 7.0
# Rings smaller than this many cells are slivers the smoothing left behind.
SLIVER_AREA = 20
MAX_POINTS_PER_RING = 300
TOWNS_PER_OKRES = 12
PRAHA_KRAJ = 19
PRAHA_OBEC = 554782


@dataclass(frozen=True)
class Seed:
    """One point the land around it is given to."""

    x: float
    y: float
    kraj: int
    # "okres:<code>", or Praha as "obec:<code>", since it lies in no okres.
    district: str
    obvod: int | None


@dataclass(frozen=True)
class Outline:
    path: str
    bbox: list[float]
    label: list[float]


def to_xy(lat: float, lon: float) -> tuple[float, float]:
    x = (lon - LON_WEST) / (LON_EAST - LON_WEST) * WIDTH
    y = (LAT_NORTH - lat) / (LAT_NORTH - LAT_SOUTH) * HEIGHT
    return x, y


class Tracer:
    """Gives every cell of the map to its nearest seed and traces the outline
    of any group of seeds."""

    def __init__(self, seeds: list[Seed]):
        self._seeds = seeds
        tree = cKDTree(np.array([(seed.x, seed.y) for seed in seeds]))
        xs, ys = np.meshgrid(np.arange(WIDTH) + 0.5, np.arange(HEIGHT) + 0.5)
        distance, nearest = tree.query(np.column_stack([xs.ravel(), ys.ravel()]))
        self._nearest = nearest.reshape(HEIGHT, WIDTH)
        near_a_village = (distance * KM_PER_CELL <= MAX_KM_FROM_A_VILLAGE).reshape(HEIGHT, WIDTH)
        # Areas with no village nearby, such as military zones, would be holes.
        self._inside = binary_fill_holes(near_a_village)

    def kraj_mask(self, kraj: int) -> np.ndarray:
        return self._inside & (self._label(lambda seed: seed.kraj) == kraj)

    def district_mask(self, district: str) -> np.ndarray:
        return self._inside & (self._label(lambda seed: seed.district) == district)

    def obvod_mask(self, obvod: int) -> np.ndarray:
        return self._inside & (self._label(lambda seed: seed.obvod) == obvod)

    def _label(self, of) -> np.ndarray:
        values = np.empty(len(self._seeds), dtype=object)
        values[:] = [of(seed) for seed in self._seeds]
        return values[self._nearest]


def outline(mask: np.ndarray) -> Outline:
    smooth = gaussian_filter(mask.astype(float), 1.2)
    filled, offsets = contourpy.contour_generator(z=smooth, fill_type=contourpy.FillType.OuterOffset).filled(0.5, 2.0)
    rings = [polygon[start:end] for polygon, ring_offsets in zip(filled, offsets)
             for start, end in pairwise(ring_offsets)]
    # A small unit like Praha 1 is a single ring smaller than a sliver.
    largest = max(rings, key=ring_area)
    parts = []
    for ring in rings:
        if ring is not largest and ring_area(ring) < SLIVER_AREA:
            continue
        step = max(1, len(ring) // MAX_POINTS_PER_RING)
        parts.append("M" + "L".join(f"{x + 0.5:.1f},{y + 0.5:.1f}" for x, y in ring[::step]) + "Z")
    rows, columns = np.nonzero(mask)
    bbox = [float(columns.min()), float(rows.min()), float(columns.max() + 1), float(rows.max() + 1)]
    # The label goes where the region is deepest, which for a ring like
    # Středočeský around Praha is not its centre.
    deepest_row, deepest_column = np.unravel_index(np.argmax(distance_transform_edt(mask)), mask.shape)
    return Outline(path="".join(parts), bbox=bbox, label=[float(deepest_column) + 0.5, float(deepest_row) + 0.5])


def ring_area(ring: np.ndarray) -> float:
    xs, ys = ring[:, 0], ring[:, 1]
    return abs(np.dot(xs, np.roll(ys, 1)) - np.dot(ys, np.roll(xs, 1))) / 2


def main() -> None:
    db = sqlite3.connect(GAZETTEER)
    kraje = dict(db.execute("SELECT code, name FROM kraje"))
    okresy = {code: (name, kraj) for code, name, kraj in db.execute("SELECT code, name, kraj_code FROM okresy")}
    obvody = dict(db.execute("SELECT code, name FROM obvody"))
    streets = dict(db.execute("SELECT obec_code, count(*) FROM ulice GROUP BY obec_code"))

    seeds = []
    towns_by_okres: dict[int, list[dict]] = {}
    for code, name, okres, kraj, lat, lon in db.execute("SELECT code, name, okres_code, kraj_code, lat, lon FROM obce"):
        if code == PRAHA_OBEC:
            continue
        x, y = to_xy(lat, lon)
        seeds.append(Seed(x=x, y=y, kraj=kraj, district=f"okres:{okres}", obvod=None))
        towns_by_okres.setdefault(okres, []).append({
            "code": code, "name": name, "okres": okres, "kraj": kraj,
            "x": round(x, 1), "y": round(y, 1), "streets": streets.get(code, 0),
        })
    # Praha's městské části give Praha its real size and its obvody.
    for lat, lon, obvod in db.execute("SELECT lat, lon, obvod_code FROM mestske_casti WHERE obec_code = ?",
                                      (PRAHA_OBEC,)):
        x, y = to_xy(lat, lon)
        seeds.append(Seed(x=x, y=y, kraj=PRAHA_KRAJ, district=f"obec:{PRAHA_OBEC}", obvod=obvod))

    tracer = Tracer(seeds)
    out_kraje = []
    for code, name in sorted(kraje.items()):
        traced = outline(tracer.kraj_mask(code))
        out_kraje.append({"kind": "kraj", "code": code, "name": name,
                          "path": traced.path, "bbox": traced.bbox, "label": traced.label})
    out_okresy = []
    for district in sorted({seed.district for seed in seeds}):
        kind, code_text = district.split(":")
        code = int(code_text)
        name, kraj = okresy[code] if kind == "okres" else ("Praha", PRAHA_KRAJ)
        traced = outline(tracer.district_mask(district))
        out_okresy.append({"kind": kind, "code": code, "name": name, "kraj": kraj,
                           "path": traced.path, "bbox": traced.bbox, "label": traced.label})
    out_obvody = []
    for code, name in sorted(obvody.items()):
        traced = outline(tracer.obvod_mask(code))
        out_obvody.append({"kind": "obvod", "code": code, "name": name,
                           "path": traced.path, "bbox": traced.bbox, "label": traced.label})
    out_obce = [town for towns in towns_by_okres.values()
                for town in sorted(towns, key=lambda town: -town["streets"])[:TOWNS_PER_OKRES]]

    out = {"width": WIDTH, "height": HEIGHT, "kraje": out_kraje, "okresy": out_okresy,
           "obvody": out_obvody, "obce": out_obce}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()
