# 2. openapi-fetch binds the panel's calls to the contract

Status: accepted (2026-09-24)

## Context

SidecarClient hand-assembled its URLs. Path strings and query keys could
silently drift from the generated contract: a renamed defaulted query
parameter yields a running app showing wrong data, with no error anywhere.
A three-lens review (dependency risk, contract integrity, codebase fit)
compared the hand-written client, point-of-use satisfies bindings, and
openapi-fetch.

## Decision

SidecarClient's internals use openapi-fetch's createClient over the
generated paths type. Every path, method, parameter name, request body,
and response is compile-checked by construction, there is no unchecked way
to make a call. The facade keeps its throw-based surface, so pages and
tests never see the library. eventsUrl stays hand-rolled, SSE sits outside
OpenAPI. The owner ruled for declarative-by-construction over
per-endpoint discipline.

## Consequences

- The panel's first runtime dependency: one file, about 4 kB gzipped, from
  the same monorepo as the type generator already in devDependencies, the
  lockfile pins it. Maintenance is effectively one person, the accepted
  failure mode is pinning the openapi-typescript and openapi-fetch pair
  indefinitely. A loopback client has near-zero CVE pressure.
- Backout is rewriting one facade file against git history, about an hour.
- Compile-time guarantees fire only when the compiler runs. The commit
  gate therefore gains a GUI type-check hook and a schema-freshness hook,
  landed as their own commits.
