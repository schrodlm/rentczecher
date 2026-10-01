# Bezrealitky

What the adapter's code does not show: the evidence behind its region ids
and search URL. The recipe for re-deriving the Prague ids lives in the
docstring of `engine/scripts/refresh_location_data.py`.

## Region ids

The search parameter `regionOsmIds` mixes two namespaces:

- Kraje and okresy use real OSM relation ids, which the portal's GraphQL API
  serves (`czechRegions(locale: CS)` on `api.bezrealitky.cz/graphql/`).
- Prague's districts use synthetic 11-digit ids outside OSM's id space. They
  exist only as a table hardcoded in the portal's frontend bundle. The API
  returns Praha with no children.

For Prague itself, the API and the search disagree: the API serves
`R435514`, while the search only recognizes `R435541`. That is why the
Prague override fires the harvest's NOTICE on every run.

Nominatim is not a source. Its relations for Praha 1 to 10 are real OSM ids
that the portal's search does not recognize as named regions.

The portal covers Praha 1 to 22. The place table ships only Praha 1 to 10,
because Sreality and RE/MAX stop there.

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
