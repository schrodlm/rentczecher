# Bezrealitky

What the adapter's code does not show: the evidence behind its region ids
and search URL. The gazetteer build reads the Prague ids from the site's
JavaScript bundle and verifies them against the live search
(`engine/scripts/gazetteer/portals/bezrealitky.py`).

## Region ids

The search parameter `regionOsmIds` mixes two namespaces:

- Kraje and okresy use real OSM relation ids, which the portal's GraphQL API
  serves (`czechRegions(locale: CS)` on `api.bezrealitky.cz/graphql/`).
- Prague's districts use synthetic 11-digit ids outside OSM's id space. They
  exist only as a table hardcoded in the portal's frontend bundle. Under
  Praha, the API lists its části obce instead (since about October 2026),
  which the search does not offer as districts.

For Prague itself, the API and the search disagree: the API serves
`R435514`, while the search only recognizes `R435541`, so the bundle's id
replaces the API's.

Nominatim is not a source. Its relations for Praha 1 to 10 are real OSM ids
that the portal's search does not recognize as named regions.

The bundle covers Praha 1 to 22. The gazetteer maps only Praha 1 to 10,
because those are the obvody. Praha 11 to 22 are městské části, which no
portal offers as a search district.

## Search URL

- `location=exact` decides whether the server applies the filters. Without it
  the page names the place but serves countrywide results.
- `osmValue` is display-only. Results are identical with the real value, a
  nonsense one, or none, and the server-side query never contains it. The
  scraper does not send it.

## Robots and a better path

The portal's `robots.txt` disallows `/vyhledat*` on the www host, which is
the page the scraper parses. The API host is not covered. Moving the scraper
to the `listAdverts` GraphQL query the portal's own frontend uses would
avoid the disallowed path and be more robust than parsing the
server-rendered page.
