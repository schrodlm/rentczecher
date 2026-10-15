When I searched a whole region for real for the first time, the inbox showed a problem I had half expected. The same flat, posted on Sreality and on Bezrealitky, sat there twice. Two rows, two photos of the same living room, and opening one left the other looking new.

## One flat, many postings

The engine already had a scored dedup matcher that decides when two listings describe the same flat. It just did nothing visible with the result. So the idea got a name: a *tracked property*, which is a flat as one profile tracks it, made of that profile's listings of it. The API now serves tracked properties instead of raw listings.

The inbox shows one card per tracked property. It leads with the cheapest listing and links to the other portals, so you can still open each posting where it was published.

## Where a fact belongs

The more interesting change was in the SQLite schema. "Viewed" and "favourite" used to live on each listing's row. That breaks as soon as a flat has two listings. You open it on Sreality, and the Bezrealitky row still claims you never saw it. And when a portal posted a flat you already knew, it showed up as new again.

The fix was a normalisation question: which entity does each fact describe? First seen, last seen and how often a posting went missing describe the posting, so they stay in `listing_tracking`. Viewed and starred describe the flat, so they moved to a new `property_tracking` table with one row per flat, which every listing of it points to. Viewing the flat on one portal now views it everywhere.

The first version of the merge had a bug. It deleted the tracking row of a listing that got left behind, so that listing vanished and came back as new. Review caught it before it was pushed.

## Prices that parse right

The same real search turned up price bugs in every scraper. RE/MAX mixed sales into a rent search, because its search form picks rent or sale by a parameter I had never sent. Reading the form found that in minutes. Its price field had also become formatted text with the district glued on, the parser failed, and the fallback read digits from the whole card, so 16 500 Kč in "Plzeň 3" came out as 316 500 Kč. Sreality showed some flats at 0 Kč, and one Bezrealitky flat came in euros.

All of that is fixed. Prices are parsed from the price field alone, plots priced per m² are multiplied out, and listings without a real price are skipped for now.

## Smaller things

The inbox got a filter next to the sort: portal, price drops only, a minimum score, layout, price, size and land. It only offers values the current listings actually have. Portal links now open in the system browser. Tauri's opener plugin would have pulled in 56 crates and almost 4 MB for that, so a small command built on the `open` crate replaced it.
