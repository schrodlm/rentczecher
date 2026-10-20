This round was about making the app nicer to live in. Every flat now has a number, a name and a picture, so it is easy to remember and point at. A flat with an exact location shows on a street map. The app can tell you how far each flat lies from the nearest metro, tram stop, school or whatever else matters to you. And the top bar and the inbox got bigger and clearer.

## A number and a name

Each profile numbers the flats it finds in the order it found them, so a flat reads like "#124 Přístavní, Holešovice · 23 000 Kč". The name is the two finest names of where it lies, its street and part of town, or its part of town and district. The number is softer than the rest, so the place leads.

The number is written into the SQLite database when a flat is found, not worked out when the inbox is shown. Counting on the fly would shift every number as old flats are forgotten after 90 days, and a number only helps if it never changes. A flat two profiles watch has two numbers, one per profile, because "#124" should mean the 124th flat this search found.

Rows and the details also show the flat's main photo as its picture, with the portal's logo small on the corner. I tried turning the photo into a coarse pixel grid, like a profile icon, but at row size the real photo is just as easy to recognise and looks better. A flat without a photo yet gets a plain gray tile with a house.

## A street map

A flat with an exact location gets a panel with a street map from OpenStreetMap, the free map anyone can edit, drawn with Leaflet, a small map library. The map opens over the whole window, and under it are links to Mapy.cz and Google Maps, for Street View and directions.

I did not put a Google map inside the app. It needs a key tied to a billing account, which an open-source app would have to ship, and it would tell Google which flats you look at. OpenStreetMap needs neither, and Google is one click away.

## What is nearby

In a flat's details you can choose kinds of places: metro, tram, train, bus, supermarket, school, kindergarten, pharmacy, park, theatre and cinema. The choice applies to every flat in the profile. The details show the nearest place of each kind with its distance, and every row in the inbox shows up to three of them.

The places come from Overpass, a public service for asking OpenStreetMap questions like "every tram stop inside this rectangle". The panel asks it once per kind for the area around all the profile's flats and measures the distances itself. Nothing is stored. It is extra information, so when Overpass is busy the distances simply do not show for a while, and the panel says so.

The public Overpass servers are run by volunteers and are often full. While I was testing, the main one refused every connection and the others were slow. So the panel now knows three servers and gives each six seconds to start answering before it asks the next. A busy server tends to hold a request rather than refuse it, and without the limit the panel would wait on the slowest one.

## A clearer top bar and inbox

The scan button is the most important button in the app, and it was the easiest to miss. It is bigger now, with a soft glow, in the middle of the bar. The profile tabs are bigger and join the inbox below them, and editing a profile is a gear inside its tab.

The new, favourite and viewed sections fold away and stay folded. The list is wider, so names fit. The rows are bigger and easier to read, and each row's score is a plain ring like the one in the details.

## Map bugs

The map library stacks its layers very high, so the street map stayed bright above the dark background of the photo viewer and the profile editor. Keeping its layers inside the map fixed it. Stepping to the next flat updated everything except the map, which kept the first flat's point. And a map created while its pane was hidden measured itself as zero size and stayed gray when the pane appeared. Now it measures itself again whenever its size changes.

## Next

All of this, together with the photos, is in version 0.2.0. Next I will watch how often the nearby places stay empty. If it is often, they could come bundled with the app, the way place names already do.
