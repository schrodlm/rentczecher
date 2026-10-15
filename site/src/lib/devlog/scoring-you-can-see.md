The profile editor is finished. Clicking + opens a window to create a profile, the pencil opens the selected one to edit or delete it, and the scoring section shows how listings would score while you set it up. Building it changed how scoring works, so most of this post is about that.

## Scoring with examples

Every listing gets a score from 0 to 100 for how well it matches your wishes: price, size, layout, place and so on. On their own, those settings are abstract. So the scoring section shows example listings next to them, scored live, one near 100, one near 50 and one near 10. When you change a setting, you see right away what it does to listings that look real.

## Weights, not importance levels

My first version let you set each preference to an importance level, from Off to Top. Underneath, those levels were turned into weights, numbers that say how many of the 100 points a preference can give. That caused a problem. Setting two preferences both to Low saved the same weights as setting both to Top, so the levels could not be read back from what was stored.

I tried three prototypes and ended up showing the weights directly, as one bar split into segments. Each preference gets a segment as wide as its weight. Dragging the divider between two segments moves points between just those two, and the arrow keys nudge it. Now there is only one thing stored and one thing you set. A level was only ever a way of showing a weight.

I also simplified the rules. A preference counts as soon as its value is set, with no extra switch to turn it on. And a preferred place is now all or nothing. In any of your places, a listing gets all of that preference's points, anywhere else it gets none. The rule is written out in points in the editor, so you can see exactly what is at stake.

## Smaller decisions

The preferred values got honest names all the way through the engine, the database, the API and the panel. `max_good_price` became `preferred_price`, for example, so the code says what the setting means.

Mistakes are caught in the form, in Czech: a missing name, place or portal, or a minimum above the maximum, keeps Save disabled with a message. If the engine still refuses something, its own reason is shown after a Czech "could not save".

Every listing in the inbox now shows its score as a ring that goes from bronze through amber to olive. Mixing olive and amber in plain RGB gave a muddy brown in the middle. Mixing them in OKLCH, a colour space built around how people see colour, keeps it bright.

## What review caught

Pressing Escape in the place search closed the whole editor and threw away the draft. The search now marks the Escape it uses for its own list, and the editor ignores those. And turning on several preferences in a row could squeeze one below its minimum weight, after which a divider moved the wrong way. Both were found in review and fixed before they were pushed.

The type checker was not enough proof that it all worked. The real test was running the whole flow against a real engine on a scratch database: create a profile, rename it, delete it, and see the engine answer each step.
