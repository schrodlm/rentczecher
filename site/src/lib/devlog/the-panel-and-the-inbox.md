The engine could now answer questions, but nothing was asking yet. This step built the panel: the part of the desktop app you actually look at. It shows the inbox of new listings by talking to the engine running alongside it. It is written in Svelte with SvelteKit, and I learned that stack while building it.

## Svelte is a compiler

The most useful thing to understand early was what kind of tool Svelte is. React ships a runtime to the browser that interprets your components as the page runs. Svelte does that work at build time instead: it compiles each component into plain JavaScript that updates the page directly. Its reactivity is a few markers in the code. `$state` marks a value as live, `$derived` computes a value from live ones, and assigning a new value is enough to redraw what depends on it.

Vite sits around all of that. It is the build tool and the development server, drives the compilers and reloads the page every time a file is saved.

## A client that cannot call the wrong address

The panel talks to the engine through `openapi-fetch`, a small typed HTTP client fed by the engine's OpenAPI description. In plain terms: if I misspell an address or pass a wrong parameter, the code does not compile. It works like a struct member access in C, checked by the compiler and gone from the shipped JavaScript.

## The browser blocked everything

The first real request failed, and so did every one after it. The panel and the engine ran on different ports, which the browser treats as different sites. Before letting the page talk to another site, it asks that site for permission with a preflight request, part of a mechanism called CORS. The engine never answered, so the browser refused. FastAPI's CORS middleware fixed it, allowing exactly the panel's own address.

The rule behind this, the same-origin policy, exists so a malicious page cannot talk to other sites in your name. It applies just as strictly to two parts of my own app.

## Czech has three plurals

The panel is in Czech, so it needed translations from day one. English has two plural forms, one and many. Czech has three: 1 byt, 2 byty, 5 bytů. A plain dictionary of strings cannot express that, so the panel uses gettext catalogues, the long-established format with plural rules built in. The code holds the English sentence where it is used, a Czech `.po` catalogue translates it, and a check refuses any commit that leaves a string untranslated.

## The inbox

Profiles became tabs across the top, from a sketch I drew over a screenshot. Next to them sit a button that runs a scan with live progress and the health of each portal, then the feed of listing cards.

Deciding when a listing counts as seen took three tries. Marking it when it scrolled past was overthought, marking it on hover felt strange in use, and a click to open it won.

## Safety nets

A commit check makes sure the OpenAPI file matches the engine's code, and GitHub Actions now tests both the engine and the panel on every push. The first run passed on its first try.
