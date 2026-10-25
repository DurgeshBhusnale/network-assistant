# ADR-0008: Stages, states and outcomes are text validated against pack config

- Status: Accepted (25 Oct 2026). Refines ADR-0006.

## Context
The schema draft used Postgres enums with Career Sprint words (`gc_stage` with `referred`/`interview`/`thanked`, `interaction_type`, `suggestion_stage`). A freelance pack ("proposal sent", "won client") would need a migration, which contradicts ADR-0006. Stage names were also inconsistent (`warmed` vs `warm_up`).

## Decision
One vocabulary everywhere:

| Concept | Column | Values | Validated by |
|---|---|---|---|
| Stage (what the next message does) | `suggestions.stage`, `drafts.stage`, `interactions.stage` | pack `stages[].id`; Career Sprint: `warm_up`, `ask`, `follow_up`, `thank` | App, against `packs.config.stages` |
| Relationship state per goal | `goal_contacts.state` | generic: `none`, `warmed`, `asked`, `replied`, `won` | DB check (generic for every pack) |
| Outcome | `goal_contacts.outcome`, `interactions.outcome` | pack `outcomes`; Career Sprint: `referred`, `interview` | App, against `packs.config.outcomes` |
| Interaction type | `interactions.type` | generic: `met`, `sent`, `replied`, `no_reply`, `note`, `outcome` | DB check; `outcome` rows must carry `interactions.outcome` |

- A thank-you is a `sent` interaction with `stage = 'thank'`; `goal_contacts.thanked_at` records it. No `thanked` state.
- `goal_contacts.state = 'won'` when any pack outcome is logged; the specific outcome is in `goal_contacts.outcome`.
- Suggestions without a goal (Stay in Touch, P1) use stage `warm_up` (a reconnect with no ask).
- `app/engine/packs.py` holds the pack config model and the validators. A synthetic second pack (`apps/api/tests/fixtures/packs/freelance_test.json`) runs through the same validators and DB writes to prove nothing is hard-coded to Career Sprint.

## Consequences
- Typos in stage values aren't caught by the DB; the app validators and tests must catch them.
- New packs need only config.
