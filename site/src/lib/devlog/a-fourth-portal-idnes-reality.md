rentczecher reads a fourth portal now, iDNES Reality. Many agencies send their listings there as well as to the other portals, so it adds flats the first three miss, and its copies of the same agency listings give the cross-portal matching real work. It is on in every new profile, next to RE/MAX.

## Checking what it asks first

Before writing any code I looked at what the portal asks of apps like this one. iDNES Reality publishes terms only for advertisers, and nothing in them is about how visitors read the site. Its robots.txt, the file where a site tells crawlers what to stay away from, allows the search pages. It rules out a few kinds of search URL, and the app never builds those: no price floor in the URL, one value per filter, and no sorting. The app applies the price floor to the results itself. By the rules the project keeps, a portal that does not ask apps to stay away is on by default, so iDNES Reality is.

I also checked that the portal answers the app as it is. Every request carries the app's own name, and the portal served it without a firewall or a challenge page in between. If that ever changes, the app leaves the portal alone, as it would any portal that refuses it.

## No API, just pages

Sreality has an API, an address that answers with JSON, data laid out for programs, and Bezrealitky tucks the same kind of data into its pages, so for those two the app reads data. iDNES Reality builds its pages on the server as plain HTML, the same as RE/MAX, so the adapter, the part of the engine that knows one portal, reads the result cards with BeautifulSoup, a Python library for picking things out of HTML. Each card gives a title with the layout and the areas, an address, a price and one photo.

The titles hide one trap. The portal groups the digits of a large area with a no-break space, "1 255 m²", while a plain space follows the layout, "3+1 120 m²". Reading every space as a thousands separator would turn that flat into 1 120 m², so only the no-break space counts.

A search with no results hides another. The page fills up with similar offers from elsewhere, and a careless reader would take them for the search's own results. The adapter reads only the results list.

## Places it already knows

Every portal names places in its own way, and for the first three portals the gazetteer, the app's offline list of every Czech place from the RÚIAN registry, keeps a table of each portal's ids. iDNES Reality turned out to name its places by their RÚIAN codes directly, "OKRES-3405" for okres Plzeň-město. The adapter builds that from the place the profile searches, and the gazetteer needed no new table at all.

## Photos

A card shows one photo, so for a flat you open the app reads the whole gallery from the advert page, as it does for Bezrealitky and RE/MAX. That gallery also holds videos and 3D tours, which the app leaves out.

## A safer upgrade

Admitting a new portal meant changing the database. A listing's portal used to be checked against a fixed list written into the table, and SQLite, the database the app keeps on your computer, cannot change such a check in place. The table has to be rebuilt. Rebuilding it the plain way would have deleted every price history and photo along with it, because SQLite removes everything that belongs to a table you drop. The migration step now switches that off while it runs and checks that no row has lost the row it belongs to before it saves. A listing's portal now points at the table of portals, so the next portal needs only one new row there.

## What the review caught

The first version put a plot's area where a house's floor area goes, so a land search's minimum plot size let every iDNES plot through. The gallery reader at first took a flat's videos and 3D tours for photos, which would have pushed real photos out of the twenty the app keeps. The upgrade could also have refused to run on a database where an outside tool had once left a row behind, and every launch after that would have failed. All three are fixed, and each one has a test.

## Next

Searches through iDNES Reality stop after fifty pages, like the others. A search of all of Praha's rentals without a price limit reaches that, so a price range is worth setting there.
