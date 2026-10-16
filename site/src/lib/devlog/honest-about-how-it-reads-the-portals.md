With the licence settled, I went looking for anything in the project that could get me into trouble or simply read badly. I went through the network behaviour, the wording of the docs, the stored data, the logos and the plans for later features, and wrote everything I found into one ranked list. Three things stood out: the app pretended to be a browser, it turned Sreality on in every new profile, and it kept every listing it ever saw forever. All three are fixed.

## Rules first

Before changing any code I wrote down the rules the fixes follow, as an Architecture Decision Record called "one private copy per person". It says that one app serves one person and their own devices, that nothing of the listings leaves the computer, that the store is a working set rather than an archive, that a refusal from a portal is a no, that a portal asking not to be read is off by default, that every listing sends you back to its portal, and that no money is tied to features. Every later feature gets checked against it.

## An honest name

Every HTTP request carries a User-Agent header, a short line saying which program is asking. Until now rentczecher sent the one Firefox sends. My old notes said Sreality refuses anything that is not a browser, but when I tested it, that turned out to be networks being blocked, not the header. All three portals answered a plain `rentczecher/0.1.0 (+https://rentczecher.cz)` exactly as before, so that is what the app sends now. A portal operator who sees it in their logs can follow the link and find out what the app is.

## Off until you turn it on

Sreality's terms forbid automated reading, and Bezrealitky's robots.txt, the file where a site tells crawlers what to stay away from, rules out the search page the app reads. So both are now off in a new profile, and only RE/MAX is on. Switching one of them on shows a short note on what the portal asks, links its terms, and leaves the choice to you.

## A memory of 90 days

The app used to forget only that a profile had seen a listing, and kept the listing itself, its price history and its place forever. Over months a broad search would have turned into an archive of a portal's listings, which is exactly what database law is written against.

Now a flat that no profile has seen for 90 days is deleted with everything read about it, unless you starred it. In SQLite the tables are linked with cascading foreign keys, so deleting a flat takes its listings, prices and places with it in one step. Deleting a profile deletes what only that profile held. A listing that comes back within the 90 days is still recognised as the same one.

## Plans and branches

The architecture doc still described a public website publishing market statistics built from users' scans. That is the kind of service that gets sued, so the plan is gone, and the decision record now says it was rejected rather than parked.

The code on the main branch was already clean, but about forty old branches on GitHub still carried real adverts from early tests. I deleted them.

## The logos stay

I thought about replacing the portals' logos with plain names. Showing a portal's icon next to its own listings, to say where a listing came from, is the kind of use trademark law allows, and the app does not use them to promote anything. So the icons stay, and if a portal ever objects, its icon goes.
