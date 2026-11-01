# iDNES Reality

What the adapter's code does not show: how the portal's search was found,
what its robots.txt rules out, and what a card's fields hold.

## Terms

The portal's terms ([reality.idnes.cz/podminky](https://reality.idnes.cz/podminky))
are terms for advertisers only, and say nothing about how visitors read the
site. Its footer forbids taking over, spreading or making available its texts
and photos without MAFRA's consent, which the app never does: it stores no
advert text and keeps photos only for the person whose search found them. With
neither its terms nor its robots.txt asking apps to stay away, the portal is
on in new profiles (checked in October 2026).

## No API

The portal is server-rendered HTML with no JSON behind its search. The only
JSON endpoint on a search page is the locality autocomplete at
`/admin.api/autocomplete-locality`, which robots.txt rules out and the
scraper does not need. The search answers the app's own User-Agent, with no
firewall in front of it (checked in October 2026).

## Search URL

The scraper submits the search form, `https://reality.idnes.cz/s/` with
`f[...]` fields, and the portal redirects it once to the results' own URL,
such as `/s/pronajem/byty/do-20000-za-mesic/plzen-mesto/`.

- `f[offer]` is `lease` or `sale`.
- `f[type]` is `flat`, `house` or `land`. Cottages are the house subtype
  `f[subtypeHouse][]=cabin`, and houses the subtype `house`, which leaves out
  cottages and the portal's "turn-key" and "other" houses.
- `f[locality]` names the place by its RÚIAN unit type and code:
  `VUSC-43` for Plzeňský kraj, `OKRES-3405` for okres Plzeň-město, `MOP-19`
  for Praha 1. These are the gazetteer's own codes, so the adapter needs no
  table of portal ids.
- `f[priceMax]` bounds the price. Pages count from 0 in `page`, which the
  first page leaves out.

## robots.txt

The portal's robots.txt allows the search but rules out some of its URLs.
The scraper stays inside it:

- No price floor in the URL. `f[priceMin]` redirects to a `cena-nad-` URL,
  which is ruled out, so the scraper drops the cheaper cards itself.
- One value per filter. Several values join with `|` in the URL, which is
  ruled out, so a search asks for one place and one estate type.
- No sorting. robots.txt rules out a sort with paging or with a price cap.
- No autocomplete, radius search or watchdog URLs.

Advert pages under `/detail/` are allowed.

## Cards

- A title names the offer and the estate, with its areas:
  "pronájem bytu 2+kk 54 m²", "prodej domu 145 m² s pozemkem 6 115 m²",
  "prodej stavebního pozemku 1 104 m²".
- The price is "14 600 Kč/měsíc" for a rental and "1 990 000 Kč" for a sale.
  A plot adds its price per m² outside the price itself. "Cena na vyžádání"
  states no price, and the scraper skips the card.
- The address is comma-separated, "Krupná, Praha 4 - Komořany" or
  "Kamensko, Blovice, okres Plzeň-Jih". Streets rarely carry a house number.
  Praha addresses name the obvod ("Praha 4"), not the městská část, which the
  advert's URL names instead ("praha-12-krupna").

## Photos

A card shows one photo. The advert page's gallery links each photo at full
size. Its carousel also opens videos and 3D tours.
