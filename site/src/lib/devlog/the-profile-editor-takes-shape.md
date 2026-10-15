With profiles in the database, the app needed a screen to edit them. I did not know yet what that screen should look like, so I started with prototypes instead of code I would keep.

## Prototypes first

I had three quite different editors built to compare, picked the one I liked, and went through three more rounds on it. The result is a window in front of the inbox. You pick the search area on a clickable map of Czechia, set numbers with sliders you can also type into, and say how much each wish matters, with example listings showing what that does to the ranking. The final prototype stays on its own branch exactly as I last saw it, as the reference for the real build.

## Scoring moved to the panel

Each listing gets a score for how well it fits your wishes. That score used to be calculated in the engine, but nothing in the engine ever used it. It is only for showing and sorting, so I moved the formula to the panel, where the editor can preview it live. Before deleting the engine's version, I recorded its scores for 39 sample listings, and the panel's version has a test that has to match every one of them.

The layout setting changed too. A room range like "2 to 3 rooms" can only describe a block of combinations. The new chips let you pick any set, like 2+kk together with 3+1, so the engine now stores the set itself.

## A map of Czechia without border data

The map is the part I am happiest with. You click a kraj to zoom in, click an okres to see its towns, and Praha opens into its districts. Town dots are sized by how big the town is, and their names never overlap.

The interesting part is that I had no border data at all, only the RÚIAN list of places with their coordinates. So the borders are computed. The country is divided into half-kilometre cells, and every cell belongs to its nearest village. A border then falls halfway between the last villages on either side, which is basically a Voronoi diagram. Land more than 7 km from any village counts as outside the country.

That gave a few surprises. Military areas like Brdy have no villages nearby, so they belonged to nothing and showed up as holes. Filling enclosed gaps fixed that, and the next cleanup briefly made Praha 1 and 2 unclickable, until it learned never to drop a region's main shape. Praha itself left an empty space in the middle of Středočeský kraj, because it is a region of its own. It now shows as part of Středočeský when you zoom in there.

The map is drawn once from the gazetteer, records which version it came from, and a test fails if the two ever disagree.

## Svelte does not draw it

The map is plain SVG, and the browser draws it. Svelte only writes the shapes into the page and keeps them up to date, the data holds the outlines, and ordinary CSS gives them their colours. I first wrote a few of those colours as fixed values, which would have broken dark mode, so now they are mixed from the palette like everything else.

## The rest of the form

Next to the map there is a search box that suggests real places as you type and works with the keyboard. It is also the way to reach anything the map does not draw, down to a single street. The other pieces are two kinds of slider with typed numbers beside them, the layout chips, and portal tiles with each portal's logo.
