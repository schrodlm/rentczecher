# Data from ČÚZK

The gazetteer and the place-picker map contain data from RÚIAN, the Czech
registry of territorial identification, addresses and real estate:
**ČÚZK, 2026**, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.cs)
on [ČÚZK's terms for spatial data](https://cuzk.gov.cz/Predpisy/Podminky-poskytovani-prostor-dat-a-sitovych-sluzeb/Podminky-poskytovani-prostorovych-dat-CUZK.aspx).
The year is that of the registry dump the shipped gazetteer was built from.

Both are modified from the source. The gazetteer keeps only each place's name,
RÚIAN code and centroid, and joins the places to the ids the portals search
by, for the portals that do not search by RÚIAN code. The map's outlines are
not RÚIAN's boundaries but are traced from those centroids. The registry
files each build used, and when it ran, are recorded in the gazetteer's `meta`
table and at the top of `czech-map.json`. The source
dataset is the
[RÚIAN exchange format](<https://cuzk.gov.cz/ruian/Poskytovani-udaju-ISUI-RUIAN-VDP/Vymenny-format-RUIAN-(VFR).aspx>),
which ČÚZK publishes with its metadata.

How the places are modelled is in [places.md](places.md), and how a listing's
location text becomes them in [locating.md](locating.md).
