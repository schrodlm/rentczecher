# Panel scripts

| Script | Does |
|---|---|
| `build-locales.ts` | Turns the `.po` catalogs into the JSON the panel loads. Runs on every `npm run dev`, `build` and `test`. |
| `extract-locales.ts` | Checks, or with `--write` updates, that the catalogs hold every string the panel uses. |
| `czech_map.py` | Draws the map of Czechia the search place is picked on. The gazetteer build runs it, and `uv run scripts/czech_map.py` redraws it by hand. |

## How the map is drawn

The map needs outlines for every kraj, okres and Praha obvod, but the
gazetteer has no borders. It only knows where each village is: one GPS point
per obec, plus one for each part of Praha. The script draws the borders from
those points alone.

1. **A grid.** Czechia becomes a grid of 900 × 522 cells, each about half a
   kilometre across.
2. **Every cell asks which village is closest to it.** It measures from its
   centre to every village's point and takes the nearest one, and with it
   that village's okres and kraj. Most cells hold no village at all. They are
   fields and forests, and they belong to whoever is nearest. So a border
   falls halfway between the last villages on either side of it.
3. **Too far from everything is outside.** A cell more than 7 km from any
   village is not Czechia. That gives the country its outer edge. Areas with
   no village that are fully surrounded by the country, like the military
   zones in Brdy or Doupov, are filled back in.
4. **A kraj is all of its cells.** That shape is a staircase of squares, so
   it is blurred a little and traced into a smooth outline.
5. **A name in the middle.** Each region's label sits at its point deepest
   inside, farthest from any edge. For Středočeský, a ring around Praha, that
   is not its centre.

The result is close but not exact. A real border follows rivers and ridges,
this one follows the villages. For picking where to search, that is plenty.

Town dots are sized by how many streets a town has, since the gazetteer
knows streets but not population. Each okres keeps its 12 biggest towns.
