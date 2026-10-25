---
description: Verify a sprint against its acceptance criteria before sign-off
argument-hint: <sprint number>
---

Verify Sprint $ARGUMENTS against docs/03-SPRINT-PLAN.md.

1. For every acceptance criterion and every listed test in the Sprint $ARGUMENTS section, show the evidence: test name + result, or the exact manual step I need to perform.
2. Run `pnpm check`, `pnpm test`, `pnpm test:int`, and `pnpm e2e` if this sprint has E2E tests. Paste the summaries.
3. Check every item of the Global Definition of Done.
4. Run the regression suite (Appendix A) items that exist so far.
5. List anything incomplete, shortcuts taken, and deviations from the docs (each needs an ADR or a PROGRESS.md note).
6. Give me a short manual test script for my Android phone (Appendix B items relevant to this sprint).
7. Update docs/PROGRESS.md with the sprint summary. Do not start the next sprint.
