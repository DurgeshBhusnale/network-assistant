# Progress

The coding agent updates this file at the end of every session. Newest entries at the top of each section.

## Current status

- **Current sprint:** Sprint 0 — Foundations (in progress)
- **Branch:** `sprint-0/foundations`
- **Last updated:** 25 Oct 2026

## Sprint checklist

| Sprint | Status | Tag | Notes |
|---|---|---|---|
| 0 Foundations | In progress | | |
| 1 Accounts and goal setup | Not started | | |
| 2 People | Not started | | |
| 3 AI drafting | Not started | | |
| 4 Engine and daily loop | Not started | | |
| 5 Capture | Not started | | |
| 6 WhatsApp assistant | Not started | | |
| 7 Billing and notifications | Not started | | |
| 8 Privacy, analytics, hardening | Not started | | |

## Current sprint stories

| # | Scope item (Sprint 0) | Status |
|---|---|---|
| 1 | Monorepo layout (apps/web, apps/api, supabase, packs, evals) | |
| 2 | Makefile targets | |
| 3 | Supabase local stack, first migration, generated seed | |
| 4 | API skeleton: config, logging + redaction, errors, health, Sentry | |
| 5 | Worker skeleton: arq settings, no-op cron, test task | |
| 6 | AI provider interface + FakeProvider + AI_MODE switch | |
| 7 | Web: tokens, fonts, base components, app shell, placeholder routes | |
| 8 | PWA: manifest, icons, service worker (offline shell) | |
| 9 | CI (GitHub Actions) | |
| 10 | PROGRESS.md initialised | ✅ |

## Decisions made during build

Kickoff review, approved by the founder on 25 Oct 2026:

- **ADR-0007:** Supabase Data API off (local + hosted); `anon` has no privileges; `authenticated` can only write user-editable `profiles` columns.
- **ADR-0008:** stages (`warm_up`/`ask`/`follow_up`/`thank`), `goal_contacts.state` (`none`/`warmed`/`asked`/`replied`/`won`) and outcomes are text, validated against pack config; DB check only on generic interaction types (`met`/`sent`/`replied`/`no_reply`/`note`/`outcome`). Synthetic second pack test proves it.
- `payments.user_id` is `on delete set null` (kept for tax records).
- `goals.starts_on` has no DB default; the API sets the user's local date.
- `profiles.plan_cache` dropped from the spec; plan is computed from `entitlements`.
- `memories.embedding` stays nullable and unused; pgvector and pg_trgm live in the `extensions` schema; embedding provider chosen in a later ADR.
- `make check` = lint + format check + typecheck; `make test` = unit tests (CLAUDE.md wins over the sprint plan).
- PWA installability verified by Playwright + DevTools + manual install (Lighthouse 12 removed its PWA category).
- Web calls the API on its own origin via Next.js rewrites (`/api/*`); phone testing via USB port forwarding (`docs/DEV-SETUP-WSL.md`).
- Tailwind v4 `@theme inline` maps `design/tokens.css` (copy script if importing from outside the app fails).
- Fake AI fixtures live in `app/ai/fake/fixtures/` (local dev also runs `AI_MODE=fake`).
- `.gitattributes` forces LF.
- No OpenRouter in repo code. `ai_calls.cost_inr` stays numeric (estimate, not money moved).
- arq kept (maintenance mode noted).
- E2E runs on PRs too while the suite takes < 5 min.
- Delete person: hard-delete related rows immediately, purge the contact row after 30 days.
- Thank-you and dated follow-up suggestions skip fatigue.
- Send cap counts the first `POST /drafts/{id}/send` per draft (`drafts.send_opened_at`).
- Free drafts: first generation counts as 1; tone changes / Another version don't count; free users max 3 regenerations per draft (`drafts.regenerations`, `FREE_REGENERATIONS_PER_DRAFT`).
- Claude Haiku allowed as a failure fallback for free drafts only, never Sonnet.
- All prompt input scrubbed of phones/emails by the redactor (tested).
- Capture text cleared on confirm/discard; unconfirmed swept after 24 h (Sprint 5). Retention jobs in Sprint 8.
- Pack config gains `sort_order` and `copy.picker_label` ("Get referred"); Goal screen gets a collapsed "Add job links (optional)" field (Sprint 1).
- New tokens: `--color-on-dark-soft`, `--color-waveform-idle`, `--color-dot-neutral`.

## Dependencies added

| Package | Where | Why |
|---|---|---|

## Open issues / questions for the human

- GitHub repo URL needed to add the remote and open the Sprint 0 PR.

## Needs manual testing on a real phone

-

## Session log

- 25 Oct 2026 — Kickoff review; decisions above approved; docs, schema draft, ADR-0007/0008 updated; Sprint 0 started.
- 25 Oct 2026 — Kickoff pack created (docs, ADRs, schema draft, pack config, design reference).
