# CLAUDE.md — Networking Assistant

You are the coding agent for this repository. Read this file fully at the start of every session, then `docs/PROGRESS.md` to see where we are.

## What we're building

An AI relationship assistant (working name `[App name]`) that turns the people a user already knows into the outcome they want. v1 = **Career Sprint**: help Indian tech professionals get job referrals through their own network. Under it sits a **generic relationship engine** (capture → remember → rank → draft → track) that later serves other goal packs (clients, sales, fundraising, hiring, vendors, alumni) **through configuration, not new code paths**.

Surfaces: a mobile-first installable **PWA** (Android Chrome first) + our official **WhatsApp** number. No native apps in v1.

## Source of truth (read before changing anything in that area)

| Doc | Use it for |
|---|---|
| `docs/00-CONTEXT.md` | Why this product exists; key research numbers |
| `docs/01-PRD.md` | What to build; requirement IDs (FR-…); product principles |
| `docs/02-TECH-SPEC.md` | How to build it: stack, architecture, data model, API, engine, AI, WhatsApp, billing |
| `docs/03-SPRINT-PLAN.md` | What to build now, tests, acceptance criteria |
| `docs/04-DESIGN-GUIDE.md` + `design/` | UI tokens, components, screen specs and reference markup |
| `docs/05-AI-PROMPTS-AND-EVALS.md` | Prompt texts (v1) and eval method |
| `docs/06-PRIVACY-CHECKLIST.md` | Privacy/DPDP requirements |
| `docs/schema-draft.sql` | Initial DB schema |
| `docs/adr/` | Decisions. To change a decision, add a new ADR; never silently diverge |
| `docs/DEV-SETUP.md` | Developer machine setup (Windows) and phone testing |
| `docs/PROGRESS.md` | Current sprint, done/next, open issues. **Update it at the end of every session** |

If docs conflict: PRD principles > ADRs > tech spec > sprint plan > design guide. If something is ambiguous or missing, **ask the human** before inventing product behaviour. Small technical choices: decide, then note them in `PROGRESS.md`.

## Product rules — never break these

1. **The user sends, never the app.** Outbound messages to contacts go only via `wa.me` links or copy-to-clipboard from the user's device. Never automate, scrape or log in to LinkedIn or personal WhatsApp. Never send on the user's behalf.
2. **Nothing leaves without a tap.** Drafts are drafts until the user sends them.
3. **No mass messaging.** Enforce the daily send cap (default 20). No bulk-send features.
4. **The WhatsApp bot only messages the user's own verified number** (`profiles.wa_phone_e164`). Every outbound call goes through a guard that enforces this.
5. **Free costs almost nothing.** Free users: no WhatsApp messages initiated by us, no frontier models, weekly cadence. All gating goes through `billing/limits.py`.
6. **Goal packs are config.** No `if pack == "career_sprint"` branches in engine code; read behaviour from `packs.config`.
7. **Store the minimum.** Delete audio after transcription. Never store WhatsApp message bodies. Never log phones, emails, message text or transcripts.
8. **Honest drafts.** Drafts may only state facts present in the user's data; warm-up drafts contain no ask. Enforced by code + fact check.
9. **Approved AI providers only:** Groq, Anthropic, Sarvam, OpenAI (STT fallback); **v1 uses Groq only** (ADR-0010). No DeepSeek first-party API. All AI calls go through `app/ai/router.py`. Never send phone numbers or emails to AI providers.

## Stack (details: tech spec §2)

- Web: Next.js (App Router) + TypeScript strict + Tailwind (tokens from `design/tokens.css`) + TanStack Query + generated OpenAPI client. Package manager: **pnpm**.
- API + workers: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, arq (Redis). Package manager: **uv**.
- DB/Auth/Storage: Supabase (Postgres + pgvector + RLS), migrations in `supabase/migrations`. Dev uses the cloud dev project (ADR-0009).
- AI: Groq only in v1 (gpt-oss-20B/120B, Whisper Large v3 Turbo / v3), ADR-0010. Model IDs only from env.
- Messaging: Meta WhatsApp Cloud API (direct). Payments: Razorpay. Push: VAPID web push. Email: Resend.

## Commands

Windows (PowerShell) or Linux; setup in `docs/DEV-SETUP.md`. Keep this list accurate.

```bash
pnpm bootstrap   # install deps (pnpm, uv), start Redis (docker)
pnpm dev         # web :3000, api :8000, worker (uses the cloud dev Supabase from .env)
pnpm check       # lint + format check + typecheck (web + api)
pnpm fmt         # auto-fix lint and formatting (web + api)
pnpm test        # unit tests (web + api)
pnpm test:int    # API integration tests (dev Supabase + Redis; every test rolls back)
pnpm e2e         # Playwright (Pixel 7) vs a production build + the API (fake AI); throwaway users, deleted after
pnpm gen-api     # regenerate TS client from FastAPI OpenAPI (commit the result)
pnpm db:push     # apply NEW migrations + seed to the dev project (ask the human first)
pnpm db:seed     # regenerate seed.sql from packs/*.json and apply it (idempotent)
```

The dev database is the cloud Supabase project (ADR-0009). Never reset it, never run destructive SQL on it, and ask before `pnpm db:push`. CI uses its own throwaway Supabase stack.

Generated files (CI fails if stale): `supabase/seed.sql` (from `packs/*.json`), `apps/web/lib/api/openapi.json` + `schema.d.ts` (from FastAPI).

Run `pnpm check && pnpm test` before saying a task is done. Run `pnpm test:int` when you touched the API, DB or workers.

## Code conventions

**General**
- Small, focused modules. Pure logic in `app/engine/`, `app/imports/`, `app/billing/limits.py` — no I/O there, fully unit tested.
- Name things by the domain words in the PRD (contact, memory, goal, pack, suggestion, draft, interaction, capture).
- No dead code, no commented-out code, no TODOs without an issue reference in `PROGRESS.md`.
- Add a dependency only when it clearly saves work; note it in `PROGRESS.md` with a one-line reason.

**Python (apps/api)**
- Type hints everywhere; mypy strict for `engine/`, `billing/`, `ai/`, `imports/`.
- Pydantic models for every request/response; never return ORM objects.
- Every query on a user-owned table is scoped by `user_id`. User requests run via `user_session()` (RLS). Workers/webhooks use the service session and must pass `user_id` explicitly.
- Error responses use the envelope `{"error": {"code", "message"}}` with codes from `app/core/errors.py`.
- Time: store UTC; compute "today" with the user's timezone (`zoneinfo`). Use an injectable clock (`app/core/clock.py`) so tests can freeze time.
- Money: integers in paise.

**TypeScript (apps/web)**
- Strict mode, no `any`. API types only from the generated client.
- Server state via TanStack Query hooks in `lib/api/`; no fetch calls inside components.
- Components use design tokens (CSS variables / Tailwind theme), never raw hex values.
- Accessibility: real `<button>`/`<a>`/`<input>` + `<label>`; `aria-label` on icon buttons; touch targets ≥ 44 px.
- Device APIs (Contact Picker, MediaRecorder, push) wrapped in `lib/device/` with feature detection and fallbacks.

**Database**
- Schema changes only via new migration files (`supabase migration new <name>`); never edit an applied migration.
- Every new user-owned table: `user_id` FK with `on delete cascade`, index, RLS enabled + owner policy, and an RLS isolation test.

## Testing rules

- Write tests with the code, not after. For engine/billing/imports logic, write the table-driven test first.
- Every endpoint: success, validation error, unauthenticated (401), and **cross-user isolation** test.
- `AI_MODE=fake` in tests and CI. Webhook tests use recorded fixtures in `apps/api/tests/fixtures/` and real signature verification.
- Freeze time for anything date-based (rankings, limits, follow-ups, briefs).
- E2E tests run on a mobile viewport (Pixel 7 emulation).
- Never weaken or delete a failing test to make CI pass. Fix the code, or explain to the human why the test is wrong.

## Workflow

1. Start of session: read `CLAUDE.md`, `docs/PROGRESS.md`, and the current sprint section in `docs/03-SPRINT-PLAN.md`.
2. For a new sprint or a large story: **plan first** (list files to create/change, tests to write, open questions) and wait for the human's OK.
3. Work story by story. One logical change per commit, conventional commit messages (`feat(engine): ranking fatigue factor`). Branch per sprint: `sprint-N/<short-name>`.
4. After each story: run checks/tests, then tick it in `PROGRESS.md`.
5. End of sprint: run the full regression suite (Sprint plan, Appendix A), verify every acceptance criterion, write the sprint summary in `PROGRESS.md`, list anything the human must test on a real phone.
6. Never push to `main`, deploy, rotate keys, or change production data without the human asking.

## Security and privacy

- Secrets only in `.env` (git-ignored) / host secret manager. Keep `.env.example` updated with every new variable (no real values).
- Verify signatures on all webhooks (WhatsApp `X-Hub-Signature-256`, Razorpay `X-Razorpay-Signature`) with constant-time compare.
- The logging redaction filter must stay on; add a test whenever you log a new field.
- Respect consents: check `consents` before contacts import, voice processing, WhatsApp messages, analytics.
- All code in this repo is written fresh for this project; do not paste code from other proprietary projects.

## Things to avoid

- Building features from later sprints or later goal packs "while you're there".
- Hard-coding model names, prices, limits, template names: they live in config/env/pack JSON.
- Calling AI providers from routes directly (always the router + a worker for anything > 2 s except drafts).
- Storing message bodies, audio after transcription, or raw webhook payloads containing message text.
- Desktop-first layouts. Design at 390 px wide first.
