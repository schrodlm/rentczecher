"""Tram stop distance enrichment for Praha 7 area.

Data from PID (Prague Integrated Transport) - data.pid.cz
"""

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.geo import haversine_m

# Praha 7 tram stops: (name, lat, lon, [daytime_lines])
# Night lines (90+) excluded from display
TRAM_STOPS = [
    ("Chotkovy sady", 50.095165, 14.409044, [2, 18, 20, 22, 23]),
    ("Dělnická", 50.103146, 14.449928, [1, 25, 34]),
    ("Holešovická tržnice", 50.09829, 14.444672, [1, 25, 34]),
    ("Hradčanská", 50.097504, 14.404309, [1, 2, 8, 18, 20, 22, 23, 25, 26]),
    ("Kamenická", 50.09964, 14.428637, [1, 8, 25, 26]),
    ("Korunovační", 50.10039, 14.419716, [1, 8, 25, 26]),
    ("Letenské náměstí", 50.099976, 14.423605, [1, 8, 25, 26]),
    ("Lotyšská", 50.104263, 14.39496, [8, 18]),
    ("Nábřeží Kpt. Jaroše", 50.09632, 14.431299, [6, 8, 12, 17, 26, 34]),
    ("Nádraží Holešovice", 50.109043, 14.439334, [1, 6, 17, 25, 34]),
    ("Nádraží Podbaba", 50.111942, 14.394094, [8, 18]),
    ("Ortenovo náměstí", 50.10772, 14.447826, [1, 25, 34]),
    ("Prašný most", 50.094788, 14.394878, [1, 2, 22, 23, 25]),
    ("Právnická fakulta", 50.091476, 14.417732, [17]),
    ("Sparta", 50.09916, 14.417687, [1, 8, 25, 26]),
    ("Strossmayerovo nám.", 50.098896, 14.43325, [1, 6, 8, 12, 17, 25, 26, 34]),
    ("Trojská", 50.116818, 14.432732, [17]),
    ("Tusarova", 50.10073, 14.450171, [1, 25, 34]),
    ("U Průhonu", 50.104923, 14.450026, [1, 25, 34]),
    ("Veletržní palác", 50.101734, 14.433063, [6, 17]),
    ("Vltavská", 50.09907, 14.438273, [1, 12, 25, 34]),
    ("Výstaviště", 50.104385, 14.431666, [1, 6, 17, 25]),
    ("Čechův most", 50.094055, 14.417288, [12, 15, 17]),
    ("Štvanice", 50.09527, 14.436951, [12]),
]




def enrich_tram(listing: Listing) -> Listing:
    """Return the listing annotated with its nearest tram stop and distance."""
    if listing.lat is None or listing.lon is None:
        return listing

    best_name = None
    best_dist: int | None = None
    best_lines: list[int] = []

    for name, lat, lon, lines in TRAM_STOPS:
        dist = haversine_m(listing.lat, listing.lon, lat, lon)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_name = name
            best_lines = lines

    if best_name is None:
        return listing
    return listing.with_annotations(
        nearest_stop=f"{best_name} (tram {', '.join(str(l) for l in best_lines)})",
        stop_distance_m=best_dist,
    )
