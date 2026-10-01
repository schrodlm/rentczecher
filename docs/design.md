# Design

The visual rules behind the panel. The color values live in
`panel/src/lib/styles/tokens.css`, and this page says how they are used.

## Palette roles

The owner's five-color palette is the whole identity. Every UI color is one of
these or a derived neutral.

| Token | Carries |
|---|---|
| ink | text, and the glyphs in the logo |
| ground | the page background |
| card | listing cards, the active sidebar item |
| line | borders and dividers |
| olive | the good semantics: price drops, healthy portal dots, high scores |
| bronze | secondary accents: labels, mid scores, accent text on the light ground |
| amber | the accent: the scan button, unread borders, the new badge, counts, the logo badge |

## Rules

- Olive is semantic and amber is brand. A price drop is never amber, and a new
  badge is never olive.
- Amber is never text on the light ground. Accent text there is bronze. In
  dark mode, bright amber text is fine.
- Text on amber is charcoal in both themes, never white.
- Type is `system-ui`, so the app speaks the OS's native face. Digits that
  align use `font-variant-numeric: tabular-nums`.
- Copy uses no em-dashes and no semicolons, in Czech and English alike.

## Logo

`panel/src/lib/assets/logo.svg` is a detective in a round amber badge, whose
fedora is a roof with a chimney and whose brim is the eaves, with shades, a
smirk and a magnifying glass. The glyphs are always charcoal. On dark or
charcoal grounds, the badge fill becomes bright amber. The minimum size is
16 px, where the chimney is the first detail allowed to blur.
