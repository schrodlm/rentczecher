# Sreality

What the adapter's code does not show: how its API was found, and how to
tell a broken scraper from a blocked network.

## The API

The scraper calls `GET https://www.sreality.cz/api/v1/estates/search`, the
endpoint the portal's own Next.js frontend uses. It replaced
`/api/cs/v2/estates` in mid-2026, when every `/api/cs/v1`, `/api/cs/v2` and
bare `/api/` path started answering 404. Bare `/api/v1/estates`, without
`/search`, answers 401 and is not the search endpoint.

The API needs a browser User-Agent. It is undocumented, so when it moves
again, the way back is the browser's network tab on a search page.

## Blocked or broken

Sreality answers 404 to every API request from some networks, datacenter
IPs among them, while its homepage still answers 200. CI runners are
datacenter machines, so the live tests never run there.

- Homepage 200 and API 404, from a residential connection: the API moved.
  Look in the network tab.
- API 404 only from one network: that network is blocked, and the code is
  fine.

## Filters fail silently

The API ignores parameters it does not know, with no error. When the
endpoint moved, the old price and area filters (`czk_price_summary_order2`,
`estate_area`) kept being accepted and filtered nothing. Their working forms
are `price_from`, `price_to` and `estate_area_from`, in snake_case only: the
frontend's camelCase spellings are ignored too. The pipeline re-applies
every filter on the client for this reason. A filter that stops working
shows up as listings outside the search, never as an error.

`category_sub_cb` takes repeated parameters. The old pipe syntax (`37|43`)
answers 422.

## Prices

Each result carries two prices. `price_czk` is per the advert's own unit,
named in `price_unit_cb`: "za nemovitost", "za měsíc", or "za m²" for many
plots and commercial spaces. `price_summary_czk` prices the whole property,
monthly for a rental, and is what the scraper reads. A plot at 17 200 Kč per
m² carries `price_czk` 17 200 and `price_summary_czk` 11 369 200.

An advert whose price is on request serves 0 in both, or a token 1 Kč, with
`price_note` such as "Info u realitního specialisty". The scraper skips it.

## Worth knowing

Search results carry `poi_*_distance` fields (metro, bus, school, shop). They
are unused today and could feed transit enrichment.
