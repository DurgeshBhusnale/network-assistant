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
| 1 | Monorepo layout (apps/web, apps/api, supabase, packs, evals) | ✅ |
| 2 | Dev commands (root `package.json` scripts, ADR-0009; Makefile removed) | ✅ `pnpm check`, `pnpm test` run on Windows |
| 3 | Supabase dev project (ADR-0009), first migration, generated seed | ✅ written, SQL parses (pglast); ⚠ not applied: project is in Seoul, awaiting region decision |
| 4 | API skeleton: config, logging + redaction, errors, health, Sentry | ✅ |
| 5 | Worker skeleton: arq settings, no-op cron, test task | ✅ |
| 6 | AI provider interface + FakeProvider + AI_MODE switch | ✅ |
| 7 | Web: tokens, fonts, base components, app shell, placeholder routes | ✅ |
| 8 | PWA: manifest, icons, service worker (offline shell) | ✅ |
| 9 | CI (GitHub Actions) | ✅ written; ⚠ first run needs the GitHub remote |
| 10 | PROGRESS.md initialised | ✅ |

### Verification so far (Windows build machine, 25 Oct 2026)

| Check | Result |
|---|---|
| API ruff + format + mypy (strict, all of `app/`) | ✅ pass |
| API unit tests (`pytest -m "not integration"`) | ✅ 64 passed |
| API integration tests (20: RLS everywhere, anon privileges, server-managed columns, second pack in DB, generic checks, no `starts_on` default, payments kept, live health, worker, anon key can't read tables) | ⚠ not run: needs the migrated dev DB and Redis |
| Seed + OpenAPI client in sync | ✅ |
| Web eslint + prettier + `tsc` | ✅ pass |
| Web unit tests (Vitest) | ✅ 26 passed |
| `next build` | ✅ |
| E2E (Playwright, Pixel 7): shell, nav, 44 px targets, no horizontal scroll at 390 px, manifest/icons, service worker control, offline page | ✅ 8 passed |
| Web → API proxy (`/api/v1/health` via :3100 → :8000) | ✅ manual (503 degraded, correct with no DB/Redis) |

## Decisions made during build

Kickoff review, approved by the founder on 25 Oct 2026:

- **ADR-0007:** Supabase Data API off (local + hosted); `anon` has no privileges; `authenticated` can only write user-editable `profiles` columns.
- **ADR-0008:** stages (`warm_up`/`ask`/`follow_up`/`thank`), `goal_contacts.state` (`none`/`warmed`/`asked`/`replied`/`won`) and outcomes are text, validated against pack config; DB check only on generic interaction types (`met`/`sent`/`replied`/`no_reply`/`note`/`outcome`). Synthetic second pack test proves it.
- `payments.user_id` is `on delete set null` (kept for tax records).
- `goals.starts_on` has no DB default; the API sets the user's local date.
- `profiles.plan_cache` dropped from the spec; plan is computed from `entitlements`.
- `memories.embedding` stays nullable and unused; pgvector and pg_trgm live in the `extensions` schema; embedding provider chosen in a later ADR.
- `pnpm check` = lint + format check + typecheck; `pnpm test` = unit tests (CLAUDE.md wins over the sprint plan).
- PWA installability verified by Playwright + DevTools + manual install (Lighthouse 12 removed its PWA category).
- Web calls the API on its own origin via Next.js rewrites (`/api/*`); phone testing via USB port forwarding (`docs/DEV-SETUP.md`).
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
- ~~Claude Haiku allowed as a failure fallback for free drafts only~~ superseded by ADR-0010 (Groq only).
- All prompt input scrubbed of phones/emails by the redactor (tested).
- Capture text cleared on confirm/discard; unconfirmed swept after 24 h (Sprint 5). Retention jobs in Sprint 8.
- Pack config gains `sort_order` and `copy.picker_label` ("Get referred"); Goal screen gets a collapsed "Add job links (optional)" field (Sprint 1).
- New tokens: `--color-on-dark-soft`, `--color-waveform-idle`, `--color-dot-neutral`.

Windows + cloud dev + Groq (25 Oct 2026, founder's decision):

- **ADR-0009:** native Windows dev, root `pnpm` scripts replace the Makefile, cloud Supabase dev project (never reset; migrations via `pnpm db:push` after asking), CI keeps a throwaway Supabase stack. `docs/DEV-SETUP-WSL.md` replaced by `docs/DEV-SETUP.md`.
- **ADR-0010:** Groq only. gpt-oss-20b (fallback 120b) for small tasks, gpt-oss-120b (fallback 20b) for all drafts, Whisper turbo (fallback large-v3) for STT. Anthropic/Sarvam/OpenAI settings removed from config and `.env.example`.
- `DATABASE_URL` accepts plain `postgresql://` (the API adds `+asyncpg`); `app/dbtasks.py` pushes migrations with the Supabase CLI and applies the seed via asyncpg.
- The "Data API disabled" integration test became "anon key can't read tables over HTTP" (works on cloud and CI); the dashboard Data API toggle is a manual checklist item.

Sprint 0 build:

- Token import from `design/tokens.css` works with Tailwind v4 + Turbopack (no copy script). Tokens are unlayered and win over Tailwind's theme layer; verified in the compiled CSS.
- Fonts via `next/font/google` exposed as `--font-bricolage`/`--font-instrument` and mapped to `font-display`/`font-body`.
- Manifest is `app/manifest.ts` (Next's typed convention) served at `/manifest.webmanifest`, not a static file in `public/`. Manifest and `themeColor` repeat token hex values (they can't read CSS variables); the no-hex test allows only those two files.
- Service worker (`public/sw.js`, hand-written) registers in production builds only; network-first navigations with `/offline` fallback, cache-first for hashed `/_next/static/`; never caches `/api/`.
- `StageBadge` takes a tone (ask / nurture / thanks) derived from pack stage config, not stage ids (ADR-0006).
- Stepper buttons are 44 px (the design file shows 38 px, below the touch minimum).
- `GET /v1/health` returns 503 with the same `HealthResponse` body when a dependency is down; each check has a 2 s timeout.
- uvicorn runs via `--factory app.main:create_app` (no app built at import time).
- Seed generator and OpenAPI exporter are modules (`python -m app.db_seed [--check]`, `python -m app.openapi_export`).
- Migration adds `drafts.regenerations` and `drafts.send_opened_at` (free regeneration cap; once-per-draft send cap), `goal_contacts.thanked_at`, `calendar_events unique (date, name)`, and column-level `insert` grants on `profiles` as well as `update`.
- Sentry `before_send` drops request bodies/cookies/query strings and auth/signature headers, masks the top-level `message`, pattern-redacts the rest.
- Logs drop uvicorn's ANSI `color_message` duplicate.
- Web calls `fetch` only through `lib/api` (ESLint `no-restricted-globals`).
- `Settings.app_env` also accepts `test`.
- jsdom pinned to 26: jsdom 30 makes Vitest workers hang at startup on the Windows machine. Retry 30 on WSL/CI later.

## Dependencies added

| Package | Where | Why |
|---|---|---|
| fastapi, uvicorn[standard], pydantic, pydantic-settings | api | Stack (tech spec §2) |
| sqlalchemy[asyncio], asyncpg | api | Stack: async Postgres |
| arq, redis | api | Stack: queue/cron (redis capped at 5.x by arq) |
| sentry-sdk[fastapi] | api | Error reporting (no-op without DSN) |
| tzdata | api | IANA timezones on Windows and slim containers (`zoneinfo`) |
| pytest, pytest-asyncio, httpx, ruff, mypy | api (dev) | Tests, lint, types |
| next, react, react-dom, tailwindcss, @tailwindcss/turbopack | web | Stack (scaffolded by create-next-app 16.4) |
| @tanstack/react-query | web | Server state (CLAUDE.md) |
| openapi-fetch, openapi-typescript | web | Typed client generated from FastAPI OpenAPI |
| vitest, @vitejs/plugin-react, jsdom@26, @testing-library/{react,jest-dom,user-event} | web (dev) | Component tests |
| @playwright/test | web (dev) | E2E, Pixel 7 emulation |
| prettier, eslint, eslint-config-next | web (dev) | Format/lint |
| concurrently | root (dev) | `pnpm dev` runs web + api + worker together |

## Open issues / questions for the human

- GitHub repo URL needed to add the remote, push `main` + `sprint-0/foundations` and open the Sprint 0 PR (CI's first run).
- **Region:** the dev project `xnjbgyjnecdgclssnquj` is in `ap-northeast-2` (Seoul), not Mumbai. Decide: recreate in `ap-south-1` (recommended) or accept Seoul for dev only. Migration not pushed until then.
- **Redis:** Docker Desktop reports "unable to start" (no WSL2/Hyper-V backend). Options: enable the backend, or use a managed Redis URL.
- Turn the Data API off in the dev project dashboard (ADR-0007).
- Supabase MCP added to `.mcp.json`; the founder must authenticate it (`claude` → `/mcp` → supabase → Authenticate) and restart the session.
- CI: verify `supabase start` with `[api] enabled = false` still serves Auth, and `supabase status -o env` prints `ANON_KEY`.
- CI action versions (`actions/checkout@v4`, `setup-node@v4`, `pnpm/action-setup@v4`, `astral-sh/setup-uv@v6`, `supabase/setup-cli@v1`): confirm on first run.
- Placeholder icons (blue square + marigold dot) until branding exists.

## Needs manual testing on a real phone

Sprint 0 (USB port forwarding, see `docs/DEV-SETUP.md` §5; use a production build `pnpm --filter web build && pnpm --filter web start` so the service worker registers):

- [ ] Open `http://localhost:3000` on Android Chrome: redirects to Today; status card shows API/DB/Redis ok.
- [ ] Bottom nav: 5 items, marigold capture button raised, active tab highlighted; tap through all tabs.
- [ ] Chrome menu → **Install app** / Add to Home screen → opens full-screen from the icon.
- [ ] Airplane mode → open People → "You're offline" page; back online → Try again works.

## Session log

- 25 Oct 2026 — Switched to Windows + cloud Supabase dev + Groq only (ADR-0009, ADR-0010); found the dev project is in Seoul; Docker backend not available.
- 25 Oct 2026 — Sprint 0 built on the Windows machine (WSL not installed yet): all scope items written; API + web lint/type/unit, build and E2E green; integration tests, Makefile and Supabase pending a WSL/CI run.
- 25 Oct 2026 — Kickoff review; decisions above approved; docs, schema draft, ADR-0007/0008 updated; Sprint 0 started.
- 25 Oct 2026 — Kickoff pack created (docs, ADRs, schema draft, pack config, design reference).
