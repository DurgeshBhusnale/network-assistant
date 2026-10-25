---
description: Plan a sprint from docs/03-SPRINT-PLAN.md and wait for approval
argument-hint: <sprint number>
---

Start Sprint $ARGUMENTS from docs/03-SPRINT-PLAN.md.

1. Read CLAUDE.md, docs/PROGRESS.md, and the Sprint $ARGUMENTS section of docs/03-SPRINT-PLAN.md, plus the PRD requirements and tech spec sections it references.
2. Check the previous sprint is marked done in docs/PROGRESS.md. If not, stop and tell me.
3. Produce a plan: stories in build order; files to create/change; migrations; endpoints; UI screens and the design file each follows; tests per story (unit, integration incl. cross-user isolation, E2E); prerequisites I must provide (keys, accounts, fixtures); open questions.
4. Wait for my approval. Do not write code until I approve.
5. After approval: create branch `sprint-$ARGUMENTS/<short-name>`, build story by story with tests, keep commits small, tick stories in docs/PROGRESS.md as you go.
