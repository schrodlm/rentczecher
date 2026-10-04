# How a listing gets its location

Every listing arrives with a location written the portal's own way, for example
`Přístavní, Praha, Holešovice, Praha 7`. The engine turns that text into a
**Location**: the official unit of each kind the text names, taken from RÚIAN,
the Czech state register of addresses. Every RÚIAN unit has a numeric code.

The lookups are done by the gazetteer, a database of every Czech unit shipped
with the app. The units themselves (kraj, okres, obec, obvod, městská část,
část obce, ulice) are described in [places.md](places.md).

This page follows one listing through the whole path.

## The result first

For the text `Přístavní, Praha, Holešovice, Praha 7`, with house number 1401,
the listing ends up with this Location:

| Kind | Unit |
|---|---|
| kraj | Hlavní město Praha |
| okres | none, Praha has no okres |
| obec | Praha |
| obvod | Praha 7 |
| městská část | Praha 7 |
| část obce | Holešovice |
| ulice | Přístavní |
| číslo popisné | 1401 |
| číslo orientační | none |

A Location holds at most one unit of each kind, because an address lies in
exactly one unit of each kind. A kind the text leaves open stays empty.

## 1. The portal's text becomes names

Each portal has an adapter, the code that reads that one portal. It is the
only code that knows the portal's format. It splits the text into plain names
and labels none of them, because whether "Holešovice" is a street or a
district is for the gazetteer to work out.

- Sreality gives separate fields (street, city, city part, district).
- Bezrealitky gives a comma-separated string.
- RE/MAX gives a comma-separated string ending with the kraj, and the town in
  the card title.

Two things the adapter does label, because no lookup could tell them apart:

- **The okres**, when the portal states it. An okres shares its name with its
  capital town, so "Domažlice" alone could be either. A labelled okres is never
  read as the town.
- **The house numbers**, when the portal gives them. Sreality has a field for
  each. RE/MAX writes `street 1419 / 1419`, repeating the číslo popisné when
  there is no číslo orientační. A single number is left out, since it does not
  say which of the two it is. The Bezrealitky adapter reads none.

## 2. The gazetteer picks the one unit the text pins down

The gazetteer looks every name up across all kinds and gathers every match into
one pool. For the example that is:

- twelve streets named Přístavní (in Praha, Brno, Mělník and more)
- the obec Praha
- two části obce named Holešovice (in Praha and in Chroustovice)
- the městská část Praha 7 (Praha also has an obvod Praha 7, which step 3
  finds)

It then picks **one** match, the anchor, by asking these questions in order:

1. **Does another name vouch for it?** A match whose obec is also named in the
   text wins. Only the Přístavní in Praha has "Praha" beside it. This is the
   strongest evidence, since street names repeat across the country.
2. **Is it the only one inside an okres the text names?**
3. **Can the name only mean one town?** "Kdyně" exists only in Kdyně. A town's
   own name means the town, not its central část obce of the same name.
4. **Failing all that, the okres the text names, if there is exactly one.** A
   coarse true answer beats a precise wrong one.

The first three questions check the most specific kind first: street, then
část obce, then městská část, then obec. A kind counts only when exactly one
candidate is left. Two candidates are a tie, and a tie moves on to the next
question. When no question settles it, the listing gets no Location rather
than a guess.

## 3. The rest of the Location fills in

From the anchor, the gazetteer fills in three things:

- **The units that contain it.** A street lies in one obec, an obec in one
  okres and one kraj, a Praha městská část in one obvod. These are certain, so
  they are always filled.
- **The other names**, each looked up only inside the anchor's obec.
  "Holešovice" is ambiguous nationwide but exactly one část obce inside Praha.
  In Praha a district number like "Praha 7" means the obvod, as it does in a
  Czech address.
- **The units its street or část obce lies in.** RÚIAN's address points show
  which část obce and městská část each street lies in, and which městská část
  each část obce lies in. Přístavní lies only in Holešovice and only in the
  městská část Praha 7, so both fill even when the text names neither, and the
  obvod follows from the městská část. A street or část obce that spans two
  units of a kind, or whose unit disagrees with one the text named, leaves that
  kind empty: Holešovice alone spans two městské části, so it leaves the
  městská část and the obvod empty.

A name fills its kind only when exactly one unit inside the obec matches. Two
names that disagree, say "Praha 6" and "Praha 7", leave that kind empty for
the street to decide. A kind the text names is never replaced. A name that
matches the obec or the okres never fills a smaller kind, though a street
lying in that kind still fills it. For example, Brno has a část obce called
"Brno-město", but when another name is the anchor, the text "Brno-město" does
not fill it, because it is also the okres.

## 4. The property keeps its most detailed location

Several postings on different portals can describe one property. The property
stores the most detailed Location any of them gave: the one with the finer
unit, and between equally fine ones, the one with a house number. A detailed
posting disappearing later never makes the stored location coarser.

Only the codes are stored, one column per kind in `property_locations`, plus
the house numbers as written. The names stay in the gazetteer.

## 5. The panel gets it back with names

When the panel asks for a profile's listings, the engine reads each property's
stored codes and looks their names up in the gazetteer for that one request.
Each listing carries:

- `resolved_location`: each kind as `{code, name}` or empty, plus the house
  numbers.
- `location_raw_text`: the portal's own text, as written.

The panel shows only `location_raw_text` for now.

## What it does not do yet

- **Units are never checked against each other.** Text that contradicts itself,
  such as "Veletržní, Praha 8" where Veletržní lies in Praha 7, is recorded as
  written. See issue #64.
- **A district name can land on the wrong unit when it is the anchor.** When
  "Praha 7" is the finest name in the text, the Location gets the městská část
  Praha 7 as well as the obvod, although an address means only the obvod. Bare
  "Brno-město" likewise lands on Brno's část obce of that name. See issue #64.
- **A wrongly resolved location stays.** The property keeps the most detailed
  location, not the most correct one, so a later coarser but correct one cannot
  replace it.
- **House numbers are not looked up.** They are kept as the portal wrote them,
  not turned into an exact point.
- **GPS never decides the unit.** A listing's own coordinates help spot the
  same property on two portals, but they never decide which unit the listing
  lies in.
