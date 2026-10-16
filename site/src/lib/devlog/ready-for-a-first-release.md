The last fixes before the first release are in, and version 0.1.0 is out as a beta. It is not finished, but it works.

## Any place, down to a street

The portals only search by region and district. A profile searching a town used to save without complaint and then never find anything, because the app could not turn a town into a portal search. Now it searches the smallest district that holds the place, and keeps only the listings that lie inside it. A listing whose location cannot be shown to be inside is left out.

## A failed scan says so

A scan without an internet connection used to finish as if it had worked, and counted every flat as missing. Now a scan that reaches no portal saves nothing and tells you to check your connection. A scan with some portals down names them.

## A cap on every search

When a search has more listings than fit on one page, the scraper reads page after page. Bezrealitky and RE/MAX used to stop only when the portal itself signalled the end. If a portal ever served its last page again, or kept a link to a next page that does not exist, the app would have asked forever.

Now every search reads at most 50 pages on each portal, the same as Sreality always did, and stops as soon as a page carries only adverts it has already read. The check counts what the portal sent, before any filtering. A first version counted the listings left after filtering, so a page whose new adverts were all filtered out would have looked like a repeat and ended a real search early.

## Releases from a tag

The installers are built by GitHub Actions on three machines, one per operating system, because PyInstaller, which packages the Python engine, can only build for the system it runs on. Until now the results were just build artifacts. Now pushing a version tag checks that the tag matches the app's version, builds all three, gives the installers names without the version, and drafts a GitHub Release with all four files. Fixed names mean a link to the latest release's file always finds the newest one, so the website's download buttons never need changing.

The draft stays private until I have installed it and published it by hand. I published 0.1.0 as a beta in its title rather than as a pre-release, because GitHub's link to the latest release skips pre-releases, and the download buttons would have led nowhere.

## One clean schema

During development the database grew through sixteen migrations, small SQL files that each change the schema a little. Some of them converted data from an earlier shape that no user ever had. Before anyone has a real database, I folded all sixteen into one file that creates the final schema directly. To be sure nothing changed, I built a database each way and compared every table, column, constraint and seeded row. They were identical.

This only works before a first release. The app records the number of the last migration it applied, and a database already at sixteen would never run a new second one.

## Credits, within reason

Python, lxml and PyYAML each carry other projects' code inside them, such as OpenSSL or libxml2, without passing those projects' licence texts along. I wrote the code to add them all to the app's notices, then decided against it. It made the notices script bigger and harder to follow for very little, and the notices already name those libraries. The AppImage, which bundles about two hundred desktop libraries of its own, turned out to be covered already, because the tool that builds it copies every library's copyright file inside.

## Next

Next come a minimum time between scans, stopping for good when a portal refuses, and signing the Windows installer so it opens without a warning.
