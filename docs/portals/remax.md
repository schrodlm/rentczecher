# RE/MAX

What the adapter's code does not show: how the search form's fields map to
the query, and what a card's price field holds.

## Search URL

The scraper builds the URL the search form at
`https://www.remax-czech.cz/reality/vyhledavani/` submits.

- `sale` picks the offer: 1 sells, 2 rents. Without it the results mix both.
- `hledani` only switches between the list (1) and the map (2). The scraper
  asks for the list, whose cards it reads.
- `types[<id>]=on` picks the estate type, and `regions[<kraj>][<okres>]=on`
  each district, ids taken from the form's trees.
- `price_from` and `price_to` bound the price, and `stranka` pages.

## Prices

A card's `data-price` holds the price as the card shows it, formatted, with
its unit in a `<small>` after the currency:

- "16 500 Kč (za měsíc)" or "45 000 Kč (vč. DPH, za měsíc)" for a rental
- "4 790 000 Kč (za nemovitost)" for a sale
- "17 200 Kč (za m²)" for some plots, which the scraper multiplies by the
  area the card names
- now and then "(za rok)" for a rental, which the scraper skips
- "Pronajato", "Prodáno" or "Cena na vyžádání v kanceláři" instead of a
  price, which the scraper skips

The card's text around the field holds other numbers, such as the district
in "Plzeň 3", so the price is read from the field alone, never from the
card's text.
