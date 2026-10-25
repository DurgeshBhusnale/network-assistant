# ADR-0006: Goal packs are configuration over a generic engine

- Status: Accepted (25 Oct 2026). Refined by ADR-0008 (stage/state/outcome vocabulary).

## Context
Career referrals are only the first goal. The roadmap adds freelance clients, event follow-up, sales, fundraising, hiring, outsourcing/vendors and alumni communities. Building each as separate code would multiply maintenance.

## Decision
- The engine (relevance, ranking, stages, triggers, drafting) is pack-agnostic and reads behaviour from `packs.config` (JSON in `packs/*.json`): goal schema, relevance labels and weights, stages, outcomes, timing boosts, fatigue, list sizes, prompt ids, copy.
- Pack-specific behaviour that config can't express goes into pack prompt templates first; a pack-specific code hook needs a new ADR.
- Data model is shared (`goals.params` jsonb, `goal_contacts.state` holds generic states; pack stages and outcomes are text, see ADR-0008).

## Consequences
- Slightly more abstraction in v1. Tests must cover the engine with at least one synthetic second pack config (e.g., `tests/fixtures/packs/freelance_test.json`) to prove nothing is hard-coded to Career Sprint.
