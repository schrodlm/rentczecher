"""PROTOTYPE, throwaway. Builds an approximate map of Czechia from the
gazetteer's points: every bit of land goes to the nearest obec (or Praha
městská část), and the outline of each kraj, okres and Praha obvod is traced
from that. Real boundaries would come from RÚIAN polygons.

Run with a Python that has numpy, scipy and matplotlib:
    python3 make_czech_map.py
"""

import json
import math
import sqlite3
from pathlib import Path

import numpy as np
from matplotlib import contour as _  # noqa: F401  (loads contourpy)
import contourpy
from scipy.ndimage import binary_fill_holes, distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
GAZETTEER = HERE.parents[4] / "engine/src/rentczecher_engine/adapters/geocoding/gazetteer.sqlite"
OUT = HERE / "czech-map.json"

LON0, LON1, LAT0, LAT1 = 12.0, 18.95, 48.5, 51.1
WIDTH = 900
SCALE = math.cos(math.radians(49.8))
HEIGHT = round(WIDTH * (LAT1 - LAT0) / ((LON1 - LON0) * SCALE))
MAX_KM = 7.0
PRAHA = 554782


def to_xy(lat: float, lon: float) -> tuple[float, float]:
    x = (lon - LON0) / (LON1 - LON0) * WIDTH
    y = (LAT1 - lat) / (LAT1 - LAT0) * HEIGHT
    return x, y


def main() -> None:
    db = sqlite3.connect(GAZETTEER)
    kraje = {code: name for code, name in db.execute("SELECT code, name FROM kraje")}
    okresy = {code: (name, kraj) for code, name, kraj in db.execute("SELECT code, name, kraj_code FROM okresy")}
    obvody = {code: name for code, name in db.execute("SELECT code, name FROM obvody")}

    # Seeds: every obec, and Praha's městské části so Praha gets its real
    # size and its obvody.
    seeds = []  # (x, y, kraj, okres_key, obvod)
    # The gazetteer has no population, but a town's street count tracks it.
    streets = dict(db.execute("SELECT obec_code, count(*) FROM ulice GROUP BY obec_code"))
    obce = []
    for code, name, okres, kraj, lat, lon in db.execute(
            "SELECT code, name, okres_code, kraj_code, lat, lon FROM obce"):
        x, y = to_xy(lat, lon)
        if code != PRAHA:
            seeds.append((x, y, kraj, f"okres:{okres}", None))
        obce.append({"code": code, "name": name, "okres": okres, "kraj": kraj,
                     "x": round(x, 1), "y": round(y, 1), "streets": streets.get(code, 0)})
    for lat, lon, obvod in db.execute(
            "SELECT lat, lon, obvod_code FROM mestske_casti WHERE obec_code = ?", (PRAHA,)):
        x, y = to_xy(lat, lon)
        seeds.append((x, y, 19, f"obec:{PRAHA}", obvod))

    points = np.array([(s[0], s[1]) for s in seeds])
    tree = cKDTree(points)
    xs, ys = np.meshgrid(np.arange(WIDTH) + 0.5, np.arange(HEIGHT) + 0.5)
    cells = np.column_stack([xs.ravel(), ys.ravel()])
    distance, nearest = tree.query(cells)
    km_per_cell = (LON1 - LON0) * SCALE * 111.32 / WIDTH
    inside = distance * km_per_cell <= MAX_KM
    nearest = nearest.reshape(HEIGHT, WIDTH)
    # Areas with no village nearby (military zones like Brdy or Doupov)
    # would be holes, so land enclosed by the country counts as inside.
    inside = binary_fill_holes(inside.reshape(HEIGHT, WIDTH))

    def outline(mask: np.ndarray) -> tuple[str, list[float]]:
        smooth = gaussian_filter(mask.astype(float), 1.2)
        generator = contourpy.contour_generator(z=smooth, fill_type=contourpy.FillType.OuterOffset)
        filled, offsets = generator.filled(0.5, 2.0)
        rings = [polygon[start:end] for polygon, ring_offsets in zip(filled, offsets)
                 for start, end in zip(ring_offsets[:-1], ring_offsets[1:])]

        def area(ring: np.ndarray) -> float:
            xs_r, ys_r = ring[:, 0], ring[:, 1]
            return abs(np.dot(xs_r, np.roll(ys_r, 1)) - np.dot(ys_r, np.roll(xs_r, 1))) / 2

        # Slivers left by the smoothing go, but never a region's largest ring,
        # which for a small unit like Praha 1 is the whole of it.
        largest = max(rings, key=area)
        parts = []
        for ring in rings:
            if ring is not largest and area(ring) < 20:
                continue
            step = max(1, len(ring) // 300)
            coords = ring[::step]
            parts.append("M" + "L".join(f"{x + 0.5:.1f},{y + 0.5:.1f}" for x, y in coords) + "Z")
        ys_, xs_ = np.nonzero(mask)
        bbox = [float(xs_.min()), float(ys_.min()), float(xs_.max() + 1), float(ys_.max() + 1)]
        # The label sits at the point deepest inside the region, which for a
        # ring like Středočeský is not its centre.
        depth = distance_transform_edt(mask)
        ly, lx = np.unravel_index(np.argmax(depth), depth.shape)
        return "".join(parts), bbox, [float(lx) + 0.5, float(ly) + 0.5]

    def labels(index: int) -> np.ndarray:
        return np.array([s[index] for s in seeds], dtype=object)[nearest]

    kraj_of = labels(2)
    okres_of = labels(3)
    obvod_of = labels(4)

    out = {"width": WIDTH, "height": HEIGHT, "kraje": [], "okresy": [], "obvody": [], "obce": obce}
    for code, name in sorted(kraje.items()):
        path, bbox, label = outline(inside & (kraj_of == code))
        out["kraje"].append({"kind": "kraj", "code": code, "name": name, "path": path, "bbox": bbox, "label": label})
    for key in sorted({s[3] for s in seeds}):
        kind, code = key.split(":")
        code = int(code)
        if kind == "okres":
            name, kraj = okresy[code]
        else:
            name, kraj = "Praha", 19
        path, bbox, label = outline(inside & (okres_of == key))
        out["okresy"].append({"kind": kind, "code": code, "name": name, "kraj": kraj, "path": path, "bbox": bbox, "label": label})
    for code, name in sorted(obvody.items()):
        path, bbox, label = outline(inside & (obvod_of == code))
        out["obvody"].append({"kind": "obvod", "code": code, "name": name, "path": path, "bbox": bbox, "label": label})

    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} kB, {WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
