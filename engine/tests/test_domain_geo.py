"""Tests for the geo primitives: haversine distance and the blocking grid.

Run: python3 -m pytest tests/test_domain_geo.py -v
"""

from rentczecher.domain.geo import CELL_LAT_DEG, CELL_LON_DEG, geocell, haversine_m

# Veletržní street, Praha - Holešovice
PRAHA = (50.101484, 14.429775)


class TestHaversine:
    def test_zero_distance_for_identical_points(self):
        assert haversine_m(*PRAHA, *PRAHA) == 0

    def test_known_distance_praha_brno(self):
        # Praha center to Brno center is ~185 km as the crow flies.
        d = haversine_m(50.0875, 14.4213, 49.1951, 16.6068)
        assert 180_000 < d < 190_000


class TestGeocell:
    def test_returns_integer_pair(self):
        cell = geocell(*PRAHA)
        assert isinstance(cell[0], int)
        assert isinstance(cell[1], int)

    def test_same_point_same_cell(self):
        assert geocell(*PRAHA) == geocell(*PRAHA)

    def test_cell_edges_are_about_1200m(self):
        lat, lon = PRAHA
        north = haversine_m(lat, lon, lat + CELL_LAT_DEG, lon)
        east = haversine_m(lat, lon, lat, lon + CELL_LON_DEG)
        assert 1100 < north < 1300
        assert 1100 < east < 1300

    def test_points_within_200m_are_same_or_adjacent_cell(self):
        # The recall guarantee blocking relies on: a true match (<200m apart)
        # is always found by querying the cell and its 8 neighbors.
        lat, lon = PRAHA
        ci, cj = geocell(lat, lon)
        for dlat, dlon in [(0.0017, 0), (-0.0017, 0), (0, 0.0027), (0, -0.0027),
                           (0.0012, 0.0019), (-0.0012, -0.0019)]:
            assert haversine_m(lat, lon, lat + dlat, lon + dlon) <= 200
            ni, nj = geocell(lat + dlat, lon + dlon)
            assert abs(ni - ci) <= 1
            assert abs(nj - cj) <= 1

    def test_boundary_point_lands_on_a_deterministic_side(self):
        # A point exactly on a cell edge belongs to the higher cell (floor semantics).
        lat = 4639 * CELL_LAT_DEG
        assert geocell(lat, 14.43)[0] == 4639
        assert geocell(lat - 1e-9, 14.43)[0] == 4638

    def test_negative_coordinates_use_floor_not_truncation(self):
        # int() truncates toward zero and would collapse cells -1 and 0 across
        # the equator/meridian; floor keeps every cell distinct.
        assert geocell(-0.001, -0.001) == (-1, -1)
        assert geocell(0.001, 0.001) == (0, 0)

    def test_czech_extremes_yield_distinct_cells(self):
        # Aš (westernmost) and Jablunkov (easternmost) must never collide.
        assert geocell(50.2239, 12.1950) != geocell(49.5763, 18.7645)
