# Architecture Decision Records

One file per decision: `NNNN-short-title.md`. To change a decision, add a new ADR that supersedes the old one (and mark the old one "Superseded by ADR-NNNN").

| ADR | Decision |
|---|---|
| 0001 | Mobile-first PWA, not native, for v1 |
| 0002 | Supabase (Mumbai) + FastAPI + Next.js |
| 0003 | One AI router; Groq for volume, Claude for high-stakes drafts |
| 0004 | The user sends; the app never messages contacts |
| 0005 | Sign in with Google/email; verify phone via WhatsApp linking |
| 0006 | Goal packs are configuration over a generic engine |

## Template

```markdown
# ADR-NNNN: Title

- Status: Proposed | Accepted | Superseded by ADR-NNNN (date)

## Context
What forces are at play; facts and numbers.

## Decision
What we will do.

## Consequences
What becomes easier or harder; follow-ups.
```
