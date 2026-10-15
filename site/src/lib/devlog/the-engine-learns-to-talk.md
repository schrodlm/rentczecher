rentczecher started as a Python command-line tool. It checked the portals, wrote down what was new and sent an email. A desktop app needs more than that. It has to ask the engine for listings, start a scan and hear back while the scan runs. So the engine got a small local HTTP API, built with FastAPI and served by uvicorn.

## One slice at a time

The API already existed as one large draft, too big to understand in one sitting. So I rebuilt it as 39 small commits and reviewed each one. First the plumbing: bearer-token auth, the run manager that executes scans, and the broker that hands out live updates. Then one feature per commit: profiles, new listings, starting a scan, portal health and the event stream.

## OpenAPI as the contract

The engine is Python and the panel is TypeScript, so they need one shared description of what goes over the wire. FastAPI derives an OpenAPI schema from the Pydantic models, and a script exports it to `docs/api/openapi.json` in the repository. On the panel side, `openapi-typescript` generates types from that file and `openapi-fetch` makes the calls with them. A check in CI fails when the committed schema drifts from the code, so neither side can change the contract silently.

## Server-Sent Events

Live updates use Server-Sent Events: one HTTP response with `text/event-stream` that never ends. The engine keeps writing small text messages into it, and the browser's `EventSource` turns each one into a callback. Behind it sits a broker that gives every subscriber its own queue and copies each event into all of them.

One wrinkle: `EventSource` cannot send custom headers, so it cannot carry the bearer token like every other call does. The event route alone also accepts the token as a `?token=` query parameter.

## Only localhost

The API binds to localhost only. Exposing it to the network would need TLS and a proper way to hand out tokens, so that waits for headless mode, where the engine runs on one machine and other devices connect to it.
