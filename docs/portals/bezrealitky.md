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

## Prices

The search asks for `currency=CZK`, and the server converts almost every
advert's `price` and `charges` to crowns, at about 24.7 Kč to the euro in
October 2026. Now and then an advert still comes back with `currency`
"EUR" and its euro amount (one in all of Plzeňský kraj on 2026-10-11). The
scraper skips any advert not in CZK. `originalPrice` is the price before the
advert's last change, not a crown equivalent.

## Photos

The search page's Apollo cache gives each advert its `mainImage` alone, as a
`RECORD_THUMB` URL. The advert's own page lists the whole gallery in its
`__NEXT_DATA__`, at `props.pageProps.origAdvert.publicImages`, each photo's
`url` the `RECORD_MAIN` size, about 1200 px tall. Tours and videos sit in
fields of their own, so `publicImages` holds only photos. The app reads that
page once, when the user opens or stars the flat.

The photos are served from `api.bezrealitky.cz`.

## robots.txt

The portal's `robots.txt` asks crawlers to stay off `/vyhledat*` and
`/search*` on the www host, the search page the scraper reads, and off the
whole API host, which serves the photos. An advert's own page is not among
the paths it lists. The portal is therefore off in new profiles, and the user
turns it on after a note that says so.
