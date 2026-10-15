The inbox used to be a feed of cards. That was fine for a quick look, but not for actually working through a few dozen flats. This step turned it into something I can use: a list beside the selected listing's details, favourites, and a proper price history.

## A list beside the details

The inbox is now a compact list on the left, split into new, favourite and already viewed listings, with the selected listing in full on the right. On a narrow window only one side shows at a time. It turned out to be a much calmer way to read many items. Your place in the list never moves while you read.

You can go through it by keyboard. Up and down move through the list, Enter opens the listing on its portal and F stars it.

Two small rules made it feel right. Selecting a listing marks it as viewed, but a profile opens on its first listing without viewing it, so just opening the app never clears what is new. And a listing you view or star keeps its place in the list until the next load, so nothing jumps away from under the cursor.

## Favourites

A star keeps a listing for the profile. Favourites get their own section under the new ones and are never cleaned away, however long the portals stop showing them.

## The details

The right side shows the price and price per m², the facts, links to every portal carrying the flat, and panels for the score, the reasons behind it and how the listing compares with the rest of the profile, for example "cheaper than 40 % of the profile's listings". There is also a map with a pin where the listing is, and a history of what happened to it. A panel with nothing to say is left out.

## Price over time

A chart shows each portal's price for the flat as a step line on one shared scale, with the current listing in amber. The history below it dates every change, rises included.

While building it I found that price drops disappeared after one scan. A drop was measured against the scan just before, and every scan records the price even when nothing changed. So on the next scan the price was "the same as last time" and the drop was gone. It is now measured against the last price that was different.

That led to a split I like. SQLite keeps every observation in a `price_observations` table, every scan and every portal, which keeps the history honest. When the API serves it, repeated prices collapse into one entry with the first and last time it was seen. Recording everything and showing only the changes are two different jobs.

## The engine does not know about the inbox

The inbox is a screen in the panel, not something the engine should care about. The engine serves listings as a profile tracks them, and each client presents them its own way. So I removed every mention of the inbox and its cards from the engine's names.
