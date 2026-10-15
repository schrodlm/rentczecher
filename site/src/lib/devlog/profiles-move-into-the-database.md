Until this step, a profile was a few lines in a YAML config file that I edited by hand. That works for one person who knows the format. It does not work for an app where you click "new search". So I moved profiles into the SQLite database as real user data, and gave the engine an API to create, change, pause and delete them. This was the groundwork for the profile editor screen.

## Profiles as tables

A profile is now spread over a few tables: the search itself, the portals it scans and the scoring preferences. I added `CHECK` constraints so the database refuses the same bad values the Python code refuses. If the two ever disagree, the database stops it.

While moving it, I cleaned up what a profile means. The list of accepted layouts became a room range plus a kitchen kind, which matches how Czech layouts like 2+kk or 2+1 actually work. Preferred neighbourhoods became preferred places, matched by where a listing really is. I also removed hidden defaults, like an assumed ideal flat size. A setting is now either chosen or empty. Pausing a profile records when it was paused instead of a plain on or off.

## A search you cannot change

I decided that a profile's search cannot be edited once it is created. The listings it has collected were found under that search. If you changed the price range or the area afterwards, all those old listings would suddenly be answering a different question. So a different search means a new profile. Everything else, including which portals it scans, can still change.

## Picking real places

Before, a profile's place was a loose name that the engine had to guess at. Now you pick a real place from a search. Typing the start of a name finds matching places from the RÚIAN register, broadest first, and the search can be limited to an area and to kinds of place. Places travel through the API as their kind and code, and come back with readable names. A profile cannot point at a place that does not exist.

I had to decide what "inside" means. Holešovice spans two Prague districts. I went with "at least partly inside", so Holešovice shows up when you search in either of them.

## Two hundred streets you could not find

Building the place search showed a bug in the gazetteer. When building its matching keys, it threw away common words like "Hlavní" (main) from every name. That made almost two hundred streets impossible to find, and it also merged some different places into the same key. I removed the rule and made each portal's scraper clean up its own odd wording instead. The gazetteer now matches names exactly as they are officially written. I rebuilt it and checked that only the matching keys changed.

## What I learned

An HTTP status code is only how the API reports a fact. "This profile does not exist" is a fact about the data. The core of the engine raises it as a normal error, and only the API layer decides that it becomes a 404. The core does not know HTTP exists.

The reviews also caught two real bugs in the new API before it was merged. A number too large for SQLite crashed the request instead of being rejected, and an infinite weight was accepted and then came back empty.
