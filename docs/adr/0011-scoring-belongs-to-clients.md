# 11. Scoring belongs to clients

Status: accepted (2026-10-06). Amends the "the engine scores" part of ADR 10.

## Context

The engine computed a 0 to 100 score for every listing a scan kept, from the
profile's preferences. Nothing in the engine acted on it. It did not decide
what is shown, new or kept, it was not stored, and since notification
channels left the engine it was not served either. The score only ever meant
something where a listing is presented: an order in the inbox, a ring on a
card, a badge in an email.

The profile editor needs the formula in the panel anyway, to show how a
listing would score while the preferences are being set. Keeping a second
copy in the engine would leave two formulas to keep in step.

## Decision

The engine stores each profile's preferences and serves them with the
listing facts a score is computed from. It computes no score.

- **Each client scores in its own way.** The panel ports today's formula.
  A notification channel that wants an order computes its own, or none.
- **The listing facts a preference reads are served,** so a client never
  needs the engine to score for it.
- **The panel's first formula is pinned to the engine's last one.** Scores
  the engine computed for sample listings are recorded as test cases before
  the engine's formula is removed.

## Consequences

- One formula exists, in the panel, where the editor previews it and the
  inbox orders by it.
- Changing how scoring works is panel work. The rule that scoring is tuned by
  feel and moves only with boundary tests pinning current behaviour applies
  there.
- A channel that wants the panel's exact order has to implement the same
  formula. Accepted: no channel needs that today.
- Rejected: a score endpoint in the engine, which keeps a formula in the
  engine that it never uses itself.
