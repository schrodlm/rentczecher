# i18n catalog approach for a Czech-default, English-switchable desktop app

## 1. Question

rentczecher is moving toward a desktop app with a Python backend (email templates,
OS toast/notification text, CLI messages) and a SvelteKit GUI webview (per
`ARCHITECTURE.md`'s roadmap, phase 4: "a Tauri and SvelteKit shell over a Python
sidecar"). User-facing strings must ship in Czech by default and be switchable to
English. What catalog/format approach should carry those strings on both the
Python side and the SvelteKit side, given one locale setting must drive both, Czech
plural correctness is mandatory, the maintainer is solo with a boring-tech bias, and
the house copy style uses em-dashes and never semicolons?

## 2. Summary

**Recommend gettext (.po/.mo)**, using Python's stdlib `gettext` module on the
backend and a build-time `.po`→JSON conversion (via `gettext-parser`, optionally
paired with `node-gettext` as the runtime) on the SvelteKit side. Gettext is the
only candidate that is simultaneously: zero-dependency on the Python side (stdlib,
no pip install), plain-text and diffable, has an exact, correctly-shaped 3-way
plural formula for Czech baked into its own reference manual, and needs nothing
heavier than a single `msgfmt` compile — no daemon, no watcher, no cloud account,
no C extension. Fluent is the strongest runner-up (nicer selector syntax, official
Python and JS bindings, no compile step at all) but its Python package has not cut
a release since 2023-03-16 (PyPI: `fluent.runtime` 0.4.0, classified alpha), a
real risk for a solo maintainer who cannot fork and patch it under time pressure.
ICU MessageFormat is disqualified on the Python side: the only real binding,
PyICU, wraps the native ICU C++ library and demands a C++ toolchain and system
library at install time — exactly the "heavy C-extension" case CLAUDE.md's
boring-tech bias flags. paraglide/inlang is JS/TS-only with no Python story at
all, so it cannot be the single system for both sides. Hand-rolled dicts are
viable in principle but externalize Czech's 3-way plural rule as something you
must get right *twice*, by hand, forever, with no structural guard against the
two catalogs drifting apart.

## 3. Constraints

- **One locale setting drives both processes.** Python backend and SvelteKit
  webview must read the active locale (`cs`/`en`) from a single source of truth,
  not two independently configured states — otherwise the toast text and the GUI
  text can disagree.
- **Czech pluralization must be correct**, not approximated as a 2-way (singular /
  plural) split. Czech has a 3-way rule (see §5).
- **Boring-tech, solo-maintainer bias.** No build daemons, no long-running
  watchers, no extra language runtimes (JVM, heavy C-extension), no SaaS/cloud
  dependency for message management. A single, understandable compile step is
  acceptable; an ongoing operational duty is not.
- **Copy style uses em-dashes and never semicolons.** Any candidate whose syntax
  reserves `—` or `;` as syntax-significant would force escaping house style;
  none of the candidates researched do this (checked explicitly per candidate),
  though classic ICU MessageFormat does reserve the straight apostrophe (§4.3).
- **Static readability over cleverness** (CLAUDE.md, general stance): prefer a
  system where the mapping from a message key to its rendered string is legible
  and format-checkable, not implicit, generated, or reflection-based.

Repo reconnaissance: this worktree has no `package.json`, no `src-tauri/`, no
webview code, and no existing i18n code. `pyproject.toml`'s runtime dependencies
are only `httpx`, `beautifulsoup4`, `lxml`, `pyyaml`, `pydantic`. The only
`locale` hit in the codebase is a `locale: CS` GraphQL parameter in
`scripts/refresh_location_data.py` (the RÚIAN geocoder API) — unrelated. Today's
user-facing strings are hardcoded Czech f-strings (e.g.
`adapters/notifiers/smtp.py`). The desktop framework choice is a roadmap
intention, not built infrastructure — the recommendation below is framework-
agnostic where it must be.

## 4. Candidates evaluated

### 4.1 gettext (.po/.mo)

**What it is.** The GNU gettext system: human-edited `.po` source files compiled
to binary `.mo` catalogs, looked up at runtime by message id (`msgid`).

**Python-side story.** `gettext` is a Python **standard-library** module — zero
external dependency. Source lives in CPython itself
(`Lib/gettext.py`).[^py-gettext] `NullTranslations` is the base translation
interface; `GNUTranslations` (a subclass) overrides `_parse()` to read `.mo`
files in either byte order.[^py-gettext] `ngettext(singular, plural, n)` selects
the plural form: "the Plural formula is taken from the catalog header. It is a C
or Python expression that has a free variable *n*; the expression evaluates to
the index of the plural in the catalog."[^py-gettext] So Python reads the
`Plural-Forms` header out of the compiled `.mo` file and evaluates it itself —
no external plural-rule table needed. Note the module reads only compiled `.mo`
files, not `.po` directly, so the `msgfmt` compile is mandatory on this side.
`NullTranslations.install(names=None)` binds `_()` (and optionally `gettext`,
`ngettext`, `pgettext`, `npgettext`) into Python's builtins namespace; calling
`.install()` again with a different translation object swaps the active language
globally.[^py-gettext]

**JS/SvelteKit-side story.** There is no first-party gettext runtime from the GNU
project for JS. The de facto standard community implementation is
`node-gettext`: "a JavaScript implementation of (a large subset of) gettext... a
pure JS runtime with no native dependencies... no build step required for
runtime use."[^node-gettext] It does not parse `.po`/`.mo` itself — you convert
files to JSON with the companion library `gettext-parser` first (which
parses/compiles `.po`/`.mo` ↔ JSON and validates `nplurals` against the
catalog's `Plural-Forms` header)[^gettext-parser], then hand `node-gettext`
pre-parsed JSON. Practical pipeline:
`.po` → `gettext-parser` (build time, once) → JSON → `node-gettext` (runtime).
No official Svelte-specific gettext integration exists; you'd wire the JSON
catalog into a small Svelte store yourself.

**Czech pluralization.** GNU gettext's own manual lists the formula for Czech
explicitly, grouped with Slovak under "Three forms, special cases for 1 and 2, 3,
4": `nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;`[^gnu-plural] This
is the exact 1 / 2–4 / 5+ split the project requires.

**Build tooling / operational weight.** `.po` is "textual, editable
files"[^gnu-po] — plain text, diffable, no special escaping for ordinary
punctuation (only `"`, `\`, and control characters need backslash-escaping
inside quoted strings[^gnu-po-entries]; em-dash and semicolon are ordinary
characters and pass through unescaped). `.mo` is a compiled binary format
(magic number `0x950412de`, sorted string tables for binary-search
lookup)[^gnu-mo], produced from `.po` by `msgfmt` — a single CLI invocation
(`msgfmt catalog.po -o catalog.mo`), not a daemon or a long-running process. No
system dependency beyond the `gettext` package's own tools (widely available,
e.g. via the OS package manager, or `pybabel compile` from the Babel Python
package as a pure-Python alternative to `msgfmt`).

**Verdict: fits.** Zero-dependency stdlib on the Python side, an exact and
authoritative Czech plural formula, plain-text source format, single-command
compile step. The one caveat is that the JS side needs one or two small
third-party packages (`gettext-parser`, optionally `node-gettext`) rather than a
first-party Mozilla- or Google-maintained JS library — acceptable, since both
are narrow, stable, widely used utility libraries rather than frameworks.

### 4.2 Fluent (Project Fluent)

**What it is.** "A research project by Mozilla" for asymmetric, natural-sounding
localization — a source message can expand into locale-specific grammar/plural
complexity that the source language doesn't need.[^fluent-home] Official
implementations exist in JavaScript, Python, and Rust.[^fluent-home]

**Python-side story.** `fluent.runtime` is the official Python implementation
under the `projectfluent` GitHub organization, providing a `Localization` class
built on `FluentBundle`, parsing `.ftl` files directly at runtime — no compile
step.[^fluent-py-repo] Its PyPI dependencies are pure Python:
`fluent.syntax`, `attrs`, `babel`, `pytz`, `typing-extensions` — no C
extension.[^fluent-pypi] **Caveat:** the last PyPI release is `0.4.0`, uploaded
2023-03-16, classified "Development Status :: 3 - Alpha"[^fluent-pypi] — no
release in roughly 2.5 years as of this writing. The GitHub repo itself is not
dormant (last push 2026-06-01, 17 open issues, not archived)[^fluent-gh-activity],
but the packaged artifact a solo maintainer would actually `pip install` has
been stale for a long time.

**JS/SvelteKit-side story.** `fluent.js` (github.com/projectfluent/fluent.js) is
the official Mozilla-maintained JS implementation, a monorepo with `@fluent/bundle`,
`@fluent/dedent`, `@fluent/dom`, `@fluent/langneg`, `@fluent/react`,
`@fluent/sequence`, `@fluent/syntax`.[^fluentjs-repo] `@fluent/bundle` parses
`.ftl` text natively at runtime, no build step. No Svelte-specific official
package exists — only React gets an official framework binding — so you would
use `@fluent/bundle` directly and hand-wire Svelte reactivity (a store wrapping
`FluentBundle`/`FluentResource`) yourself.

**Czech pluralization.** Fluent's selector syntax uses CLDR plural categories
directly, not a numeric index: "For selectors which are numbers, the variant
keys either match the number exactly or they match the CLDR plural category for
the number,"[^fluent-selectors] with categories `zero`/`one`/`two`/`few`/`many`/
`other` depending on what the target locale defines.[^fluent-selectors] Example
from the official guide:

```
emails =
    { $unreadEmails ->
        [one] You have one unread email.
       *[other] You have { $unreadEmails } unread emails.
    }
```

For Czech this would use `[one]`, `[few]`, `[many]`, `*[other]` — see §5 for the
exact CLDR rule each category maps to.

**Escaping / copy style.** Curly braces `{ }` are placeable delimiters and are
the only characters disallowed directly in message text (a literal brace is
written via the string-literal placeable `{"{"}`); inside *quoted* text, `"` is
escaped as `\"` and `\` as `\\`.[^fluent-special] The official guide uses
em-dashes directly in example prose as ordinary characters requiring no
escaping[^fluent-special], and nothing in the syntax guide gives semicolon any
reserved meaning. Fluent syntax is safe for this project's copy style.

**Build tooling / operational weight.** Pure runtime parsing of `.ftl` text
files on both sides — no compiler/codegen step at all. On this one axis Fluent
beats gettext: a single canonical `.ftl` file per locale can be read by both
runtimes with no conversion, where gettext needs `msgfmt` (Python side) and a
`.po`→JSON conversion (JS side).

**Verdict: fits, with a maintenance-risk caveat.** Technically the best-designed
option (CLDR-native selectors, official bindings on both sides, no escaping
friction, zero build step), but the Python package's alpha classifier and
2.5-year release gap are a real risk for a solo maintainer betting a production
app on it — a breaking change in a newer Python version or a bug found in
production would have no obvious upstream release to pull.

### 4.3 ICU MessageFormat / MessageFormat 2 (MF2)

**What it is.** ICU MessageFormat is ICU's long-standing pattern syntax for
argument/plural/select-based message formatting, using
`{variable, plural, =0{...} one{...} other{...}}`-style syntax with CLDR plural
categories.[^icu-mf] Its successor, **MessageFormat 2 (MF2)**, has been
standardized: "The Unicode MessageFormat Standard is a stable part of CLDR. It
was approved by the CLDR Technical Committee and is recommended for
implementation and adoption... The normative version of the specification is
published as part of TR35."[^mf2-status] Some advanced features (default
functions, the `u:` namespace) remain in Draft status as of the current
spec.[^mf2-status]

**Python-side story.** The classic path is **PyICU**, a Python extension
wrapping the native ICU C++ libraries.[^pyicu-readme] This is a heavy, non-pure-
Python dependency: "PyICU is a python extension implemented in C++ that wraps
the C/C++ ICU library... building PyICU from the sources on PyPI involves more
than just a `pip` call" unless ICU is already installed on the
system.[^pyicu-readme] It requires ICU headers/libraries and `pkg-config`
present at build time, `-std=c++11` compiler flags, matching the Python
distribution's C++ compiler on macOS, and `LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH`
configuration at runtime on Linux/macOS unless a prebuilt OS package is
used.[^pyicu-readme] No official pure-Python MF2 implementation was found.

**JS-side story.** `intl-messageformat` (FormatJS) is a pure-JS implementation
of ICU Message syntax with no WASM or native dependency — it "uses industry
standards: ICU Message syntax and CLDR locale data," relying on the browser/
Node's built-in `Intl.NumberFormat`/`Intl.DateTimeFormat`/
`Intl.PluralRules`.[^intl-mf] FormatJS also publishes `@formatjs/svelte-intl`,
an official Svelte binding (peer dependency: Svelte 5), actively maintained —
version 2.1.1 published 2026-09-18, verified against the npm
registry.[^svelte-intl-npm] A *native* JS-engine `Intl.MessageFormat` does not
exist: the TC39 proposal is at **Stage 1** (last presented February 2024 per its
README) and has not shipped in any browser or JS engine.[^tc39-mf]

**Czech pluralization.** Same CLDR plural-category model as Fluent (`one`/`few`/
`many`/`other`) — see §5. Syntax example: `{numPhotos, plural, =0 {You have no
photos.} =1 {You have one photo.} other {You have # photos.}}`.[^intl-mf]

**Escaping / copy style.** ICU MessageFormat reserves the ASCII apostrophe `'`
as its escape character: "a pair of ASCII apostrophes always represents one
ASCII apostrophe," and the guide recommends using the curly/typographic
apostrophe `’` (U+2019) in human-readable text and reserving the straight `'`
(U+0027) for syntax.[^icu-mf] This is a real, if minor, friction point —
writers must remember to use the typographic apostrophe or double any literal
straight one. No special handling of em-dash or semicolon exists.

**Build tooling / operational weight.** `intl-messageformat` itself needs no
compiler step (pure runtime parsing, like Fluent). The dealbreaker is entirely
on the Python side.

**Verdict: doesn't fit (Python side).** PyICU's native C++ dependency and
build/runtime library-path fragility is exactly what CLAUDE.md's boring-tech,
solo-maintainer bias rules out. Using classic ICU MessageFormat or MF2 would mean
either accepting PyICU's operational weight, or hand-writing a from-scratch
Python MF2 interpreter — neither is reasonable for this project's stated
priorities, even though the JS side (including the official Svelte binding) is
excellent.

### 4.4 paraglide (inlang)

**What it is.** "A compiler-first internationalization library for JavaScript/
TypeScript frameworks" that compiles message catalogs (plain local JSON files,
e.g. `messages/cs.json`, configured via a `project.inlang/settings.json`
directory) into type-safe, tree-shakeable ESM functions at build time, rather
than doing runtime string lookups.[^paraglide-home] Part of the broader inlang
ecosystem, whose other pieces — Fink (web editor), Sherlock (VS Code
extension), Parrot (Figma plugin), and a CLI — are **optional**: "No account
required; inlang tools are optional."[^inlang-home] No cloud/SaaS dependency:
message files are plain version-controlled JSON in the repo.

**Python-side story.** None. "Paraglide JS is exclusively JavaScript/
TypeScript — no Python support," targeting React, SvelteKit, TanStack Start,
React Router, Astro, Vue, Solid, and vanilla JS/TS.[^paraglide-home] No Python
SDK, plugin, or output target exists anywhere in inlang's docs or the `opral`
GitHub org. This alone disqualifies it as *the* single system spanning both
processes.

**JS/SvelteKit-side story.** First-class: SvelteKit is explicitly a supported
framework via a Vite plugin, and paraglide is one of the official Svelte CLI
add-ons (`npx sv add paraglide`) — Svelte-team-blessed tooling.[^svelte-cli-pg]
Note SvelteKit itself has **no first-party i18n system or official guidance of
its own** — it defers entirely to the ecosystem, of which paraglide is the
best-integrated option today.[^svelte-cli-pg]

**Czech pluralization.** CLDR-based via `Intl.PluralRules`; plurals are declared
per-message with selector blocks in the JSON message format, e.g.
`"declarations": ["input count", "local countPlural = count: plural"]` with
`"match": {"countPlural=one": ..., "countPlural=other": ...}` — Czech would add
`countPlural=few` and `countPlural=many` variants.[^paraglide-variants] An ICU
MessageFormat 1 input plugin also exists.[^paraglide-home]

**Build tooling / operational weight.** This is the candidate CLAUDE.md's
"build daemon / compiler step that must never drift from source" warning maps
onto most directly: setup requires `npx @inlang/paraglide-js init`, a Vite
plugin registered in `vite.config.ts`, and the compiler emits generated files
(`./paraglide/messages.js`, `./paraglide/runtime.js`); "file watching happens
automatically during development."[^paraglide-home] That is a per-build
compiler-and-generated-output pattern living permanently in the tree — exactly
the kind of indirection the project's static-readability stance is wary of (a
generated file a reader must trust matches its source), even though, credit
due, it needs no cloud account and no JVM.

**Verdict: doesn't fit.** No Python story at all, so it cannot be the single
catalog system for this project regardless of how good its Svelte integration
is. Pairing it with a *different* system on the Python side reintroduces the
"two independently-configured catalog systems that can drift" problem the
project is trying to avoid — worse than gettext's minor asymmetry (stdlib vs.
two small JS utility libraries, same source file format on both sides).

### 4.5 Hand-rolled dicts (do-nothing baseline)

**What it is.** A Python dict/module (e.g., `MESSAGES_CS`, `MESSAGES_EN`) and a
parallel JS/TS object, each mapping message keys to strings, with manual
`if n == 1: ... elif 2 <= n <= 4: ... else: ...` branching written by hand at
each plural call site (or centralized in one small helper function per side).

**Python-side story.** No dependency at all — plain dict literals or a small
`match`/`if` helper.

**JS/SvelteKit-side story.** No dependency at all — plain object literals.

**Czech pluralization.** Entirely the author's responsibility to get right, by
hand, in (at minimum) two places — once per language runtime. The formula is
simple to write once looked up (`n == 1 → one`, `2 <= n <= 4 → few`, else
`many`-bucket for the integer case; see §5 for the CLDR nuance around
non-integers, which this project likely never hits since listing counts are
whole numbers), and it can be pinned with a boundary test per side. But nothing
enforces it stays correct, stays identical on both sides, or gets applied at
every call site that needs it. The deeper risk is **drift**: nothing enforces
that every key added to the Czech dict has a matching English entry (or that the
Python and JS keysets agree). A missing key fails silently at runtime
(`KeyError`, `undefined`, or wrong-language fallback) rather than at
catalog-compile time — unlike gettext, where `msgfmt` fails loudly on a
malformed catalog and `msgfmt --statistics` makes untranslated entries visible.
Guarding against drift by hand means writing and maintaining a custom keyset-
diff test, which undercuts the "no extra tooling" appeal of doing nothing.

**Escaping / copy style.** None — plain string literals, so em-dash and
semicolon are non-issues by construction.

**Build tooling / operational weight.** Zero. The lightest possible option by
definition.

**Verdict: fits, with real risk accepted knowingly.** It satisfies every
boring-tech constraint trivially, at the cost of pushing correctness and
sync-drift entirely onto manual discipline and code review — the exact
trade-off gettext's tooling is designed to catch mechanically instead. Given
the project's own stance ("a few extra lines that fail loudly... beat a clever
one-liner that fails silently" — CLAUDE.md), a system where a missing
translation fails *silently* cuts against the project's own stated values more
than gettext's modest extra moving parts do. Reasonable only as a stopgap.

## 5. Czech pluralization reference

Two independent standards define Czech plural behavior; both were verified
against primary sources and agree for integers (1 → its own form, 2–4 → a
second form, 0 and 5+ → a third form), though they carve the categories
differently — gettext uses 3 numeric indices, CLDR uses 4 named categories
because CLDR also separates out **non-integer** values.

### GNU gettext plural formula for Czech (`cs`)

From the GNU gettext manual's Plural-Forms table, listed alongside Slovak under
"Three forms, special cases for 1 and 2, 3, 4":

```
nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;
```

Source: <https://www.gnu.org/software/gettext/manual/html_node/Plural-forms.html>[^gnu-plural]

Index 0 = "one" bucket (`n==1`, e.g. "1 nabídka"), index 1 = "few" bucket
(`n∈{2,3,4}`, "2 nabídky"), index 2 = everything else (0, 5+, "5 nabídek").
A Czech `.po` entry has exactly `msgstr[0]`, `msgstr[1]`, `msgstr[2]`.

### CLDR plural category rules for Czech (`cs`)

From the Unicode CLDR Language Plural Rules chart:

| Category | Rule | Example values | Sample |
|---|---|---|---|
| `one` | `i = 1 and v = 0` | `1` | "1 den" |
| `few` | `i = 2..4 and v = 0` | `2~4` | "2 dny" |
| `many` | `v != 0` | `0.0~1.5, 10.0, …` | "1,5 dne" |
| `other` | (everything else) | `0, 5~19, 100, 1000, …` | "5 dní" |

Source: <https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html>[^cldr-cs]
(`i` = the integer digits of the number; `v` = the number of visible fraction
digits, per UTS #35's plural-operand definitions[^tr35-operands] — so `v = 0`
means "displayed as a whole number" and `v != 0` means "displayed with a decimal
part," which is why CLDR's `many` for Czech is really "any non-integer value,"
not a fourth integer bucket.)

**For this project**, pluralized quantities (new listings, price drops, days on
market) are non-negative integers, so the CLDR `many` category never triggers in
practice — effective behavior collapses to the same 1 / 2–4 / 0-and-5+ split
gettext expresses directly. Both standards agree once decimals are off the
table, which they are here.

## 6. Recommendation

**Use gettext**, with the standard `.po`/`.mo` split, structured as:

```
locales/
  cs/
    LC_MESSAGES/
      rentczecher.po      # Czech source strings (human-edited)
      rentczecher.mo      # compiled at build/release time via msgfmt
  en/
    LC_MESSAGES/
      rentczecher.po
      rentczecher.mo
```

for the Python side, loaded via
`gettext.translation("rentczecher", localedir=..., languages=[locale])` and —
better, given the static-readability stance — called through explicit
`translation.gettext(...)`/`translation.ngettext(...)` methods rather than the
`install()`-into-builtins pattern, since an explicit object is traceable by a
reader and a type checker where a globally injected `_()` is not (a judgment
call worth confirming with the owner, see §8). Every module that currently
f-strings a Czech user-facing string (e.g. `adapters/notifiers/smtp.py`'s email
bodies, future CLI/toast text) routes through those calls instead.

On the SvelteKit side:

```
webview/src/locales/
  cs.json    # produced from locales/cs/.../rentczecher.po via gettext-parser
  en.json    # produced from locales/en/.../rentczecher.po via gettext-parser
```

with either `node-gettext` reading the JSON at runtime inside a small Svelte
store, or — since a desktop UI's catalog is small — the JSON hand-loaded into a
plain reactive object plus a five-line Czech plural-bucket function, using
`gettext-parser` purely as a build-time `.po`→JSON conversion. That keeps the
webview's runtime dependency surface at or near zero and treats gettext as the
*source format and authoring workflow* rather than a JS runtime dependency —
worth deciding once the actual message volume is known. Either way the `.po`
files are the single authored source for both sides.

**Single source of truth for the active locale**: the compiled catalogs are
per-side, but the *choice* of locale (`cs` vs `en`) must come from one place.
Given the roadmap's Tauri + SvelteKit + Python-sidecar shape, the natural owner
is **the app's persisted user config**, already owned by the Python backend
today (`adapters/config/schema.py`, `paths.py`) — add a `locale: cs | en` field
there. The Python sidecar then passes the resolved locale to the webview at
launch through whatever channel already configures the webview (a Tauri IPC
command, an initial-state injection, or a URL param — this project has not yet
chosen or built that channel, so this is necessarily generic: "whatever
mechanism the Python sidecar already uses to hand the webview its initial
state, extended with one more field"). Either way, the locale is read once from
the single config, never independently guessed per process — e.g. never let the
webview infer locale from `navigator.language` while the backend infers it from
`LANG`; that is exactly the two-independently-configured-states failure mode
the constraints rule out.

**Why gettext over Fluent** (the closest competitor): Fluent's design and CLDR-
native selector syntax are objectively nicer, its bindings are official on both
sides, and it needs no compile step at all — a genuine argument in its favor
that one research pass in this evaluation weighted as decisive. It was overruled
by the Python-side dependency picture: `fluent.runtime` is an alpha-classified
package with no PyPI release since 2023-03-16, while gettext's Python story
needs no external package at all (stdlib) — the strongest possible boring-tech
answer — and its Czech plural formula is authoritative and explicit in the
format's own reference manual. The `msgfmt` step this trades for is a single,
loud-failing CLI call, which the constraints explicitly deem acceptable. If
`fluent.runtime` resumes regular releases, or the project's message complexity
grows past flat plural buckets (heavy grammatical gender/case agreement, which
Fluent handles more gracefully), revisit — but that is not the situation
described here.

## 7. Rejected alternatives and why

- **ICU MessageFormat / MF2** — rejected on the Python side. PyICU's native C++
  dependency (system ICU library, `pkg-config`, matched compiler flags, runtime
  library paths) is precisely the "heavy C-extension" operational weight
  CLAUDE.md's solo-maintainer bias warns against, even though the JS side
  (`intl-messageformat`, plus an official and actively-maintained
  `@formatjs/svelte-intl`) is strong. Native `Intl.MessageFormat` in JS engines
  is TC39 Stage 1, shipped nowhere.
- **paraglide/inlang** — rejected outright: no Python story whatsoever, so it
  cannot serve as the single system spanning both processes. Pairing it with a
  separate Python-side system would recreate the two-independently-configured-
  catalogs problem the project explicitly wants to avoid, and its compiler-
  generates-tracked-output architecture (per-build Vite-plugin codegen) is a
  heavier build-tooling footprint than gettext's single `msgfmt` step. Notably
  it is cloud-optional — the disqualifiers are structural, not SaaS lock-in.
- **Hand-rolled dicts** — not rejected as unworkable, but not recommended as
  primary: it satisfies boring-tech constraints trivially but pushes both
  plural-rule correctness and catalog-sync correctness onto unenforced manual
  discipline, which cuts against the project's stated preference for approaches
  that fail loudly over ones that fail silently.
- **Fluent** — genuinely close second, not structurally rejected; deferred to
  gettext on the Python dependency-maturity picture alone (see §6).

## 8. Open questions / risks

- **Desktop framework not yet chosen in this repo.** No `package.json`,
  `src-tauri/`, or webview code exists in this worktree — only
  `ARCHITECTURE.md`'s roadmap naming Tauri + SvelteKit + a Python sidecar as
  the phase-4 plan. The exact channel by which the Python process hands the
  webview its initial locale (Tauri IPC command vs. injected initial state vs.
  a shared config file read by both) is not evidenced anywhere in the repo and
  should be confirmed once that scaffold exists, rather than assumed from this
  research.
- **`gettext.install()` vs. explicit translation objects** — this report
  recommends explicit `translation.gettext(...)` calls over the
  builtins-`_()`-injection pattern on static-readability grounds. That is a
  judgment call by this research, not a fact from a primary source; the owner
  should confirm it matches their taste. (Note the conventional `_()` name also
  eases `xgettext`/`pybabel extract` string extraction — the extraction keyword
  is configurable, so an explicit style can keep extraction working, but that
  wiring should be verified when set up.)
- **Whether `node-gettext` is needed at all on the JS side**, or whether a
  pre-built JSON catalog plus a hand-written five-line plural-bucket function
  is simpler — worth revisiting once the actual SvelteKit string count is
  known. `gettext-parser` as a build-time-only tool is the floor either way.
- **Fluent's Python package staleness is ambiguous.** Verified via PyPI's JSON
  API (`fluent.runtime` 0.4.0, uploaded 2023-03-16, alpha classifier) and the
  GitHub repo's `pushed_at` (2026-06-01, not archived). A package not releasing
  while its repo stays active could mean the maintainers consider 0.4.0
  feature-complete rather than abandoned — this is presented as a risk factor,
  not a certainty. One of the four independent research passes behind this
  report weighed Fluent's zero-build-step advantage as decisive and would have
  recommended Fluent; a human wanting to re-litigate should weigh exactly this
  trade (no compile step + official bindings vs. stdlib + stale-alpha
  third-party package).
- **The GNU manual's `Translating-plural-forms` page** (which would confirm the
  msgstr index-to-category mapping in the manual's own words) intermittently
  rate-limited during research (HTTP 429). The mapping stated in §5
  (0=one, 1=few, 2=other) follows unambiguously from the ternary formula's
  evaluation order, but a human citing the mapping in docs may want the
  manual's own phrasing from
  <https://www.gnu.org/software/gettext/manual/html_node/Translating-plural-forms.html>.
- **CLDR's `many` category and non-integer counts** — this app's pluralized
  counts are integers today, so CLDR's decimal-only `many` bucket for Czech
  never triggers; flagged in case a future feature (average price, percentage
  change, "1,5 km") introduces a decimal quantity that would need routing
  through `many` correctly.

[^py-gettext]: Python docs, `gettext` module — <https://docs.python.org/3/library/gettext.html>
[^gnu-plural]: GNU gettext manual, Plural forms — <https://www.gnu.org/software/gettext/manual/html_node/Plural-forms.html>
[^gnu-po]: GNU gettext manual, The Format of PO Files — <https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html>
[^gnu-po-entries]: GNU gettext manual, PO File Entries — <https://www.gnu.org/software/gettext/manual/html_node/PO-File-Entries.html>
[^gnu-mo]: GNU gettext manual, The Format of MO Files — <https://www.gnu.org/software/gettext/manual/gettext.html#MO-Files>
[^node-gettext]: node-gettext — <https://github.com/alexanderwallin/node-gettext> (npm registry: version 3.0.1, published 2026-01-06, per <https://registry.npmjs.org/node-gettext>)
[^gettext-parser]: gettext-parser — <https://github.com/smhg/gettext-parser>
[^fluent-home]: Project Fluent — <https://projectfluent.org/>
[^fluent-py-repo]: python-fluent (fluent.runtime) — <https://github.com/projectfluent/python-fluent>
[^fluent-pypi]: PyPI, `fluent.runtime` — <https://pypi.org/project/fluent.runtime/> (verified via <https://pypi.org/pypi/fluent.runtime/json>: version 0.4.0, classifier "Development Status :: 3 - Alpha", `requires_dist` = fluent.syntax, attrs, babel, pytz, typing-extensions; upload_time 2023-03-16)
[^fluent-gh-activity]: GitHub API, `projectfluent/python-fluent` — <https://api.github.com/repos/projectfluent/python-fluent> (`pushed_at`: 2026-06-01, `archived`: false, `open_issues_count`: 17)
[^fluentjs-repo]: fluent.js — <https://github.com/projectfluent/fluent.js>
[^fluent-selectors]: Fluent Syntax Guide, Selectors — <https://projectfluent.org/fluent/guide/selectors.html>
[^fluent-special]: Fluent Syntax Guide, Special Characters — <https://projectfluent.org/fluent/guide/special.html>
[^icu-mf]: ICU User Guide, Formatting Messages — <https://unicode-org.github.io/icu/userguide/format_parse/messages/>
[^mf2-status]: Unicode message-format-wg (MessageFormat 2) — <https://github.com/unicode-org/message-format-wg>
[^tc39-mf]: TC39 proposal, Intl.MessageFormat — <https://github.com/tc39/proposal-intl-messageformat> (README: "Stage: 1"; last presentation listed February 2024; no shipping engine noted)
[^pyicu-readme]: PyICU on PyPI / GitHub — <https://pypi.org/project/PyICU/> and <https://github.com/ovalhub/pyicu>
[^intl-mf]: FormatJS, intl-messageformat — <https://formatjs.github.io/docs/intl-messageformat/>
[^svelte-intl-npm]: npm registry, `@formatjs/svelte-intl` — verified via <https://registry.npmjs.org/@formatjs/svelte-intl> (`dist-tags.latest`: 2.1.1, published 2026-09-18, peer dependency Svelte 5)
[^paraglide-home]: Paraglide JS — <https://paraglidejs.com/> (redirected from <https://inlang.com/m/gerre34r/library-inlang-paraglideJs>)
[^paraglide-variants]: paraglide-js docs, variants — <https://github.com/opral/paraglide-js/blob/main/docs/variants.md>
[^svelte-cli-pg]: Svelte CLI docs, paraglide add-on — <https://svelte.dev/docs/cli/paraglide>
[^inlang-home]: inlang — <https://inlang.com/>
[^cldr-cs]: Unicode CLDR, Language Plural Rules — <https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html>
[^tr35-operands]: Unicode UTS #35, Part 3 (Numbers), Plural Operand Meanings — <https://www.unicode.org/reports/tr35/tr35-numbers.html#Operands>
