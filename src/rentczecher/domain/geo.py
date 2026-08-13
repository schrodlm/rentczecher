import math

# A geocell is one tile of a grid over the map, roughly 1.2 x 1.2 km, named
# by its integer (row, column). Two nearby points are always in the same or
# neighboring tiles, so finding properties near a point is an integer lookup,
# not a distance scan.
#
# 1 degree of latitude is ~111 km everywhere: 1.2/111 = 0.0108. A degree of
# longitude is only ~71.6 km at Czech latitudes (cos(50) * 111): 1.2/71.6 =
# 0.0168. Changing these constants renumbers the grid, so every stored
# geocell would have to be recomputed.
CELL_LAT_DEG = 0.0108
CELL_LON_DEG = 0.0168


def geocell(lat: float, lon: float) -> tuple[int, int]:
    """Grid cell indices containing the point."""
    return (math.floor(lat / CELL_LAT_DEG), math.floor(lon / CELL_LON_DEG))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Great-circle distance in whole meters."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
