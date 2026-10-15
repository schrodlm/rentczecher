A portal tells you where a flat is with a line of text, something like "Praha 7, Holešovice, Dělnická". For a person that is enough. For a program that has to answer "is this flat in Holešovice?", it is not. Names repeat across the country, portals write them differently, and free text cannot be compared reliably.

So every listing now gets a structured location: the street, the part of town, the district, the municipality and the region, each as a place from RÚIAN, the Czech state register of addresses, plus the house number when the portal gives one. A place is identified by its RÚIAN kind and code, never by its name.

## A gazetteer in SQLite

The places live in a gazetteer, a read-only SQLite database built from RÚIAN exports and a harvest of how the portals actually spell their locations. It ships with the engine and is rebuilt by a script, never edited by hand.

## Resolving the text

The resolver starts from certainty. It first finds the one place the text pins down unambiguously, usually the street. Every larger place it lies in follows from RÚIAN's hierarchy. Only then does it look up the remaining names, and only inside that municipality, where they are no longer ambiguous.

An address lies in exactly one place of each kind. But streets and parts of town cross district borders, so the most precise place alone cannot tell you the rest. That is why the `property_locations` table keeps every level instead of only the smallest one.

## When unsure, leave it empty

This became the rule for the whole feature. A missing level is harmless. A wrong one quietly misleads everything built on top of it, from search areas to the dedup matcher.

A property listed several times keeps the most precise location any of its listings gave, and a vaguer listing later on never downgrades it.

## Surprises

RE/MAX writes one house number twice, which would have stored a fake second number. Live data confirmed it, so that case is handled. And a fix I had planned for RE/MAX's Prague listings turned out to be unnecessary. They already resolved almost perfectly, and my change only made them worse, so it never shipped.

For now the location is stored and served by the API. Showing it in the panel, and letting profiles search and prefer real places, comes next.
