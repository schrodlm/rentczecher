# How rentczecher uses the portals

rentczecher is an independent project. It is not affiliated with, endorsed by
or connected to any of the portals it reads, and their names and logos belong
to their owners.

## The portals it reads

| Portal | In a new profile |
|---|---|
| [Sreality.cz](https://www.sreality.cz) (Seznam.cz) | off, asks apps not to read it |
| [Bezrealitky.cz](https://www.bezrealitky.cz) | off, asks apps not to read it |
| [RE/MAX Czech](https://www.remax-czech.cz) | on |

How each one is read, and its quirks, is in [portals/](portals/).

## Made for one person's own home search

rentczecher runs on your computer and reads the portals only for the searches
you set up in it. There is no server behind it, nothing is shared between the
people who use it, and nothing it reads is republished. Every listing links to
its posting on the portal, where you read the advert and contact the seller.

Each portal has its own terms of use. When you run rentczecher, you are the
one using the portal, so following those terms is up to you. Professional use,
as an agent or an investor for example, is outside what rentczecher is made
for.

## How it reads a portal

- **It names itself.** Every request carries the User-Agent
  `rentczecher/<version> (+https://rentczecher.cz)`, so a portal can always
  tell rentczecher apart from a browser.
- **It reads what a search needs.** A scan asks each portal for the profile's
  search and reads the result pages, with a pause between pages. It opens an
  advert's own page only when you open or star that flat in the app and the
  search results left out its photos, once, for the photos alone. It does not
  store advert descriptions.
- **It does not get around a refusal.** No proxies, no rotating identities, no
  ways past a block. A portal that refuses rentczecher is left alone.

## Portals that ask not to be read

Some portals ask automated clients to stay away, in their terms of use or
their `robots.txt`. Those are off in a new profile. Turning one on shows a
short note on what the portal asks, with a link to its terms, and the choice
is yours.

## What it keeps

rentczecher keeps a listing for as long as one of your profiles still follows
it. A listing no profile has seen for 90 days is deleted, with its price
history, its photos and everything else read about it, unless you starred it.
Deleting a profile deletes what only that profile held.

Photos are fetched the way you would look at them. After each scan, each new
flat gets its main photo, the one the portal's search results show anyway.
A flat's other photos are fetched only when you open or star it in the app.
The photos stay on your computer and are shown only inside the app, with the
portal they came from.

## For portal operators

If you run one of these portals and have a concern about how rentczecher uses
it, please [open an issue](https://github.com/schrodlm/rentczecher/issues).
Every such request gets a quick answer.

The rules rentczecher holds itself to are recorded in
[ADR 12](adr/0012-one-private-copy-per-person.md).
