Once you open a flat, it moves to Viewed and you stop thinking about it. That was fine until a flat I had looked at got cheaper and I only noticed by chance. The app knew about the drop, but the flat sat quietly in Viewed. A viewed flat that turned up on another portal did the opposite and came back as New, which it is not. Now a viewed flat that changes moves into its own Updated section, and its history shows what changed.

## An Updated section

The section sits right after New, because a change on a flat you were considering matters almost as much as a new flat. A viewed flat lands there when a scan finds one of three things: another portal posting it, a price going down, or a price going up. Opening the flat again, or "Mark all viewed", moves it back to Viewed. A starred flat stays in Favourites, where you keep it, and gets a small "Changed" mark under its star instead.

In the engine this is one new column in SQLite, the database the app keeps on your computer. Each flat a profile tracks has a row in `property_tracking`, which already held when you viewed and starred it. A migration adds `updated_at` there. A scan sets it on a viewed flat that changed, and viewing the flat clears it. The FastAPI endpoint that serves the inbox passes it along, and the event the engine sends over Server-Sent Events when a scan finds something now also fires when it found only updated flats.

## A new flat means a new flat

A flat in rentczecher is made of its postings, one per portal. The scan used to call a flat new when its surviving posting was new, so a known flat that another portal posted counted as new again. Now a flat is new only when none of its postings was seen before. The same rule decides updated: a flat you viewed with at least one posting that is new or has a different price.

## Showing what changed

A flat's history used to follow only the posting its card leads with. It now lists the price changes on every portal that posts the flat, and says when another portal started posting it. When you open an updated flat, the details start with a short "Changed since you viewed it" list, and the same rows stand out in the history, so you do not have to hunt for the change.

The list starts from the first time you opened the flat, not the last, because the app stores only the first time. Storing the last view too would narrow it down, and that is left for later.

## Two bugs in the timing

With two profiles, prices were compared against the last price any profile saw. If the second profile scanned first, the first one never saw the drop. Each profile now compares against the price its own scans last saw.

The history showed "also posted on" for every flat found on two portals at once. The two postings were saved a few microseconds apart, because each save asked the clock again, so one seemed to come after the other. Everything a scan saves now carries the scan's one time.

## Trying it by eye

The app's test scenarios are YAML files that describe scans and what the user did, replayed through the engine's own pipeline. They could only describe what you did after the last scan. Now each scan can say which flats you opened and starred right after it, so a scenario can tell the story of a flat you looked at that changed later. A new one shows price drops and rises, a new portal, a changed favourite and a flat that stayed the same, and the app opens on it with one environment variable.

## Stricter matching

The engine merges listings that describe the same flat with a scored matcher. Being within 100 m on the same street already scored over the match line, and no gap in price or size could pull a pair back under it. In my own database that had merged pairs 16 m² apart and pairs 30% apart in price.

A pair over the line now merges only when the property agrees as well. Prices have to be within 10% for every estate type. A flat also needs the same layout and sizes within 6 m², a house the size or the plot, and land the plot. A pair that does not agree is kept as uncertain and never merged. On my database the new rule undid 17 of 37 merges. The cost is that some real duplicates, such as one flat listed with and without its service charges, now show twice, which is the lesser harm.

The first version asked every estate type for a layout and a size, which houses and plots often lack, so they never merged at all. The review caught that, and each type now has its own rule.

## Version 0.4.0

This, the stricter matching and iDNES Reality make version 0.4.0. It is the first release the updater can offer, so if you are on 0.3.0, the app offers 0.4.0 in its top bar. Updating keeps all your data.
