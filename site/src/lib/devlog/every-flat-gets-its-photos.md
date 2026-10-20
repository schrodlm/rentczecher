Flats have photos now. After each scan the app keeps each new flat's main photo, the one the portal's results show anyway. When you open or star a flat, it fetches the rest of that flat's gallery, up to twenty photos. In the app the photos lead a flat's details as a collage, and any photo opens over the whole window.

## Only what a person would look at

The rule from the start is one private copy per person. Downloading a full gallery for every listing after every scan would break it with a single broad search, so the app fetches photos the way a person browsing would. Every new flat gets its main photo, at most a hundred per portal in one scan, newest first. What does not fit waits for the next scan. Only a flat you open for a moment, or star, gets its whole gallery. A flat you only scroll past never gets more than its main photo.

Marking a flat viewed is not enough to ask for its gallery, because the inbox can mark everything viewed at once. Opening it in the details is.

## Galleries from the advert page

Sreality's search results already list every photo of a flat. Bezrealitky and RE/MAX only show one, so for those the app reads the flat's own advert page once, when you open it, and takes the gallery from there. It is the only time the app opens an advert itself, and the docs and the page for portal operators now say so.

## Polite fetching

Photos come one at a time with a pause between them. A portal that refuses is asked nothing more in that round, and a photo that keeps failing is given up after three tries. RE/MAX serves full-size uploads of a few megabytes, and I kept them as they are rather than shrink anything.

The photos are plain files in the app's data folder, and they live as long as their flat. When a flat is forgotten after 90 days, or its profile is deleted, its photos go too. The panel loads each one from the engine, the Python program running in the background, through a signed link, a link that carries a secret and only works while the engine runs.

## The collage

A flat's details now open with its first photos in a collage of different sizes, shaped by how many there are, with the last tile counting the rest. While photos download, each missing one is a soft breathing wash in the app's colours. A flat without photos gets a slim banner with the portal's logo. I picked the collage from a prototype with three layouts.

Any photo opens over the whole window. The arrow keys step through the gallery, Escape closes it, and a credit links back to the advert. While more photos are on the way, it says so.

## What the review caught

One Bezrealitky advert page with an unexpected shape made the reader fail in a way nothing counted, and since the same page was tried first in every round, it would have stopped every download. Now an odd page counts as a failed read and is given up after three, like a photo.

While a gallery downloads, the engine announces every new photo to the panel. An older answer arriving late could leave the collage stuck on fewer photos than it had, so only the newest answer counts now. A Bezrealitky or RE/MAX flat also flashed "this listing has no photos" for a second before its advert page was read. Its gallery now counts as still downloading until then.

## Next

The website's screenshots still show the app without photos, because they come from made-up demo data and never from real adverts. Next the demo data gets stand-in photos of its own.
