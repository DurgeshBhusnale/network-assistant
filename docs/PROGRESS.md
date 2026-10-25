# Progress

The coding agent updates this file at the end of every session. Newest entries at the top of each section.

## Current status

- **Current sprint:** Sprint 7 — Billing and notifications (Sprints 0–6 done)
- **Mode (founder, 25 Oct 2026):** build fast; testing deferred. No new automated tests and no E2E runs until the core sprints are done; each sprint ends with `pnpm check`, existing unit tests, a production build and a live API smoke run against the dev project. A full test pass (unit, integration incl. cross-user isolation, E2E, regression suite) happens after the core sprints.
- **Branch:** `sprint-6/whatsapp` (all sprint branches pushed; each builds on the previous)
- **Last updated:** 25 Oct 2026

## Sprint checklist

| Sprint | Status | Tag | Notes |
|---|---|---|---|
| 0 Foundations | Done | | Phone check passed (founder) |
| 1 Accounts and goal setup | Done (tests deferred) | | Live API smoke passed; needs Google/email auth config in Supabase |
| 2 People | Done (tests deferred) | | Live API smoke passed incl. 1,000-row import in 7.5 s |
| 3 AI drafting | Done (tests deferred; evals runner deferred) | | Live Groq smoke: 17 calls ₹0.25, rules + fact check + free caps verified |
| 4 Engine and daily loop | Done (tests deferred) | | Live smoke of the full loop passed (ranking → draft → send → reply → referred → thank → progress) |
| 5 Capture | Done (tests deferred; Hinglish STT check pending real voice notes) | | Live smoke: extraction, possible-match, follow-up date, audio deleted + audit |
| 6 WhatsApp assistant | Done in dry-run (tests deferred) | | Needs Meta credentials + approved templates to go live |
| 7 Billing and notifications | Not started | | |
| 8 Privacy, analytics, hardening | Not started | | |

## Current sprint stories

| # | Scope item (Sprint 0) | Status |
|---|---|---|
| 1 | Monorepo layout (apps/web, apps/api, supabase, packs, evals) | ✅ |
| 2 | Dev commands (root `package.json` scripts, ADR-0009; Makefile removed) | ✅ `pnpm check`, `pnpm test` run on Windows |
| 3 | Supabase dev project (ADR-0009), first migration, generated seed | ✅ applied to the dev project with `pnpm db:push` |
| 4 | API skeleton: config, logging + redaction, errors, health, Sentry | ✅ |
| 5 | Worker skeleton: arq settings, no-op cron, test task | ✅ |
| 6 | AI provider interface + FakeProvider + AI_MODE switch | ✅ |
| 7 | Web: tokens, fonts, base components, app shell, placeholder routes | ✅ |
| 8 | PWA: manifest, icons, service worker (offline shell) | ✅ |
| 9 | CI (GitHub Actions) | ✅ written; ⚠ first run needs the GitHub remote |

### Final verification (Windows, dev project + Docker Redis, 25 Oct 2026)

| Check | Result |
|---|---|
| `pnpm check` (ruff, format, mypy strict; eslint, prettier, tsc) | ✅ |
| `pnpm test` | ✅ API 65 passed, web 26 passed |
| `pnpm test:int` against the dev project + Redis | ✅ 20 passed |
| `pnpm e2e` (Pixel 7) | ✅ 8 passed |
| `pnpm dev`: web :3000, API :8000, worker; `/v1/health` direct and via web | ✅ `{"status":"ok","db":"ok","redis":"ok"}` |
| Every table has RLS (automated) | ✅ |
| Anon key can't read tables over HTTP | ✅ 401 permission denied (Data API itself still on: dashboard toggle pending) |
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

Sprint 6:

- **Rule 4 over the tech spec:** messages from numbers that aren't linked get **no reply** (the spec suggested one sign-up reply). The only outbound path is `WhatsAppClient`, whose guard looks up `profiles.wa_phone_e164` itself and refuses users without a verified number, not opted in, or opted out (except the single STOP confirmation).
- Without `WA_ACCESS_TOKEN`/`WA_PHONE_NUMBER_ID`/`WA_GRAPH_VERSION` the client runs **dry**: guard + `wa_messages` metadata (`status='dry_run'`), nothing sent.
- Linking: `POST /v1/whatsapp/link-code` (needs the `whatsapp` consent) → 6-char code (no 0/O/1/I), 15 min, single use → `wa.me/<our number>?text=START CODE`. Webhook `START CODE` sets the number + opt-in with the service role (server-managed columns, ADR-0007); a number linked elsewhere is moved. `GET /v1/whatsapp/status` (masked number), `DELETE /v1/whatsapp/link`.
- Webhook `/v1/webhooks/whatsapp`: GET verify (constant-time token compare); POST verifies `X-Hub-Signature-256` (HMAC-SHA256, constant time) → dedupes by `wa_message_id` (unique) → records metadata only → enqueues `handle_whatsapp` with `keep_result=0` so message text never lingers in Redis → 200. Status callbacks update `wa_messages.status`. Inbound rows get the user id once the sender is resolved.
- Commands: exact keywords only (START/STOP/HELP/TODAY, case-insensitive, trimmed); anything else is a note → capture pipeline (`wa_text`); voice notes are downloaded from Meta, transcribed in memory (never stored), then the same pipeline (`wa_audio`, needs voice consent); shared contacts import via the picker path (needs contacts consent). Capture replies offer Save (only when nobody needs a merge decision) / Edit in app (`/capture?id=…`).
- Daily brief (cron every 15 min, `WA_BRIEFS_ENABLED`): paid + opted in + not opted out, at local nudge time, once per local day, template `daily_brief_v1` with quick replies `show_drafts` / `snooze_today`. Show drafts sends each draft as its own message (generating missing ones within plan limits); Snooze today snoozes today's list.
- Entitlement checks tolerate 2 min of clock skew between app servers and the DB (found in the smoke: laptop 1.2 s behind Supabase).

WhatsApp templates to submit to Meta (category **Utility**, language English):

| Name | Body | Buttons |
|---|---|---|
| `daily_brief_v1` | `Good morning {{1}}. Today's people to reach out to:` / `1. {{2}}` / `2. {{3}}` / `3. {{4}}` / `Tap Show drafts to get your messages ready.` | Quick reply: `Show drafts`, `Snooze today` |
| `sprint_reminder_v1` | `Your Career Sprint has {{1}} days left. Referrals so far: {{2}}.` | URL: `Open app` → `<APP_BASE_URL>/today` |
| `capture_ready_v1` | `Saved your note. I found {{1}} people for you to check.` | URL: `Review in app` → `<APP_BASE_URL>/today` |

Sample values for review: {{1}} Rohan; {{2}} Ananya Kulkarni — Target company; {{3}} Vikram Joshi — Birthday today; {{4}} Priya Nair — Met at eChai.

Sprint 5:

- Migration `20261025020000_captures_bucket.sql`: private `captures` bucket (16 MB, audio types). Only the service role touches it: `POST /captures/upload-url` signs a one-time upload URL for `{user_id}/{uuid}.{ext}`; the browser PUTs the audio; the API rejects storage paths outside the user's folder.
- Voice consent required for upload URLs and audio captures (403); text capture needs none. Voice memories from a Person page pass `contact_id`; everything attaches to that person.
- Worker `process_capture`: download → Groq Whisper (turbo → large-v3) → delete audio immediately + `audit_log` row → `extract_people.v1` (capture time and weekday in the user's timezone resolve "Monday") → candidates with possible matches (rapidfuzz token-set ≥ 85, company agreement ±) → `ready`. Never auto-merges. If no queue is available the API processes inline.
- Follow-up dates are kept only if on/after the capture day and within a year. Confirm writes contacts (new or merged; fills blank company/title only), memories ("Met at …", facts, "You promised: …"), a `met` interaction at the capture time, and a forced suggestion on the follow-up date (pack `follow_up` stage, else `reconnect`; free plan: that week's list).
- Confirm and discard clear `captures.transcript` and candidate text (`extracted` keeps only counts). Hourly cron `sweep_captures`: deletes audio still stored after 1 h, clears unconfirmed capture text after 24 h.
- `ai_calls` logs transcription with `audio_seconds` and cost (`ai_price_inr_per_audio_hour`).
- Web: Capture screen (recorder with live level bars + timer + 5-min cap, Type instead, uploading/processing states, confirm cards: Save / Yes merge / New person / Edit / Skip, Save to your people, Discard this note), voice memory from Person page. The unused placeholder page and its copy were removed.
- Pending: the 20-note Hinglish/Hindi voice test (needs the founder's recordings) to decide whether Whisper is good enough or Sarvam should be proposed (ADR-0010).

Sprint 4:

- Pack stages gain a `role` (`reconnect`/`ask`/`follow_up`/`thank`); the engine reasons about roles, never stage ids (ADR-0006/0008). Pack copy adds `relevance_reasons`, `outcome_labels`, `outcome_past`, `state_labels`, `stage_past`, `funnel_labels`, `success_label`, `minutes_per_person`. Pack config changes need `pnpm db:seed` on the dev DB.
- `app/engine/ranking.py` (pure): score = R·W·T·E·(1−F) per tech spec; unlabelled contacts get R = 0.3 until the LLM labels them; thank-yous skip fatigue; daily cap groups contacts by the matched target company ("Razorpay" = "Razorpay Software Pvt Ltd"), else by `company_norm`.
- Timing signals computed at ranking time (birthday incl. Feb 29, festival from `calendar_events` as a global boost, met recently from `met` interactions, job change from `triggers`); no separate daily triggers job.
- `goal_contacts.state` only moves forward (none → warmed → asked → replied → won); funnel counts come from interactions on the goal (distinct contacts).
- Ranking keeps forced (capture follow-up, Sprint 5) and acted-on suggestions; re-ranking replaces only unacted pending ones; older pending/opened expire. First `GET /today` ranks synchronously (FR-ONB-2).
- Free plan: one list per week (`for_date` = Monday), paid: daily. Nightly cron every 15 min ranks users whose local time just passed 02:00; LLM relevance labelling is an arq task queued after goal creation and import commits (skipped silently if Redis is down).
- Send: `POST /drafts/{id}/send` returns the `wa.me`/LinkedIn link; the first call per draft per local day counts toward `DAILY_SEND_CAP` (429 `SEND_CAP_REACHED`); 422 `NO_PHONE`. Sent is recorded only via `POST /interactions` (type `sent` + `draft_id`) after the user confirms ("Sent?" on return, or Mark as sent).
- `POST /interactions` handles sent/replied/no_reply/outcome; outcome validated against pack outcomes, sets `won`, adds a thank-you suggestion to the current list.
- Routes read the app's own settings (`app.state.settings`), so tests/workers can pass their own.
- Analytics batched per request (`track_many`).
- Performance: first `GET /today` ≈ 11 s and later views ≈ 2 s from a laptop in India to the Seoul dev DB (~140 ms round trip; first use of each statement/type on a pooled connection costs extra round trips). In production the API and DB share the Mumbai region (~1 ms), so the < 3 s target is expected to hold; verify on staging. Engine work itself is milliseconds.
- Web: Today (greeting, goal strip, person cards with reasons and snooze/not-relevant sheet, empty states), send panel (WhatsApp, Copy for LinkedIn, Mark as sent, "Sent?" on return), Did they reply? (Replied / Not yet / pack outcomes, thank-you card), Progress (north star, days left, funnel, by company), replies badge. The Sprint 0 system-status card and `useHealth` were removed.

Sprint 3:

- `GroqProvider` (OpenAI-compatible chat + transcription; `reasoning_effort=low` for gpt-oss; JSON mode). `AIRouter.complete_json`: per model 1 retry on retryable errors with jitter → task fallback model (20b↔120b); Pydantic validation with one repair retry; every attempt logged to `ai_calls` with an INR estimate from `ai_price_inr_per_mtok` (config).
- Prompts are plain `{{var}}` templates (conditionals computed in code); `render()` PII-scrubs every value. `style_summary.v1` returns JSON `{summary}` (doc 05 said plain text). Prompt texts were tuned during the live smoke before first release: strict language/script line, no gendered address words, fact-check accepts paraphrases.
- Draft pipeline: generate → code rules (≤ 90 words, warm-up ask detector, unexpected links, Devanagari in English/Hinglish) + fact check → one regeneration with fixes → leftovers returned as `warnings`/`unsupported_claims` for the UI to highlight.
- Drafts need an active goal (409 `NO_ACTIVE_GOAL`); stage validated against the pack before limits. AI calls happen outside DB transactions.
- `billing/limits.py`: free = 3 new drafts per local calendar month (counted from `drafts.created_at`), 3 regenerations per draft (`drafts.regenerations`); sprint fair use via `entitlements.drafts_used` (incremented with the service role). 402 codes `FREE_LIMIT_REACHED`, `FREE_REGEN_LIMIT_REACHED`, `FAIR_USE_REACHED`.
- Regenerations overwrite the same draft row (text, tone, model); edits go to `final_text`.
- Web: stage chooser sheet (stages from the active goal's pack), draft screen (tone chips, Another version, check-before-sending panel, autosave on blur, Copy), writing-style step + Settings page, static Upgrade screen. Send on WhatsApp/LinkedIn come with Sprint 4.
- Deferred to the testing phase: `evals/` runner and golden set.

Sprint 2:

- `app/imports/` (pure): normalisers (E.164 via `phonenumbers`, default IN; per-word smart casing; LinkedIn → `https://www.linkedin.com/in/<slug>`; company suffix stripping), parsers (LinkedIn CSV with preamble and 4 date formats, vCard via `vobject` incl. yearless BDAY stored with year 1904, Contact Picker), dedupe (phone → email → LinkedIn, never name; union arrays, fill blanks; different company on a known contact = job change → `job_change` trigger).
- Imports stage a preview (`imports.preview` holds candidates) and re-plan at commit against current contacts; commits are idempotent (already committed → same result). Commit runs in-request (bulk insert + executemany update; 1,000 rows in 7.5 s on the Seoul dev DB), not a worker: deviation from the sprint plan's ">200 rows in a worker"; revisit if imports get slower.
- Imports need the `contacts` consent (403 `CONSENT_REQUIRED`); manual add doesn't (it isn't an import). Manual add/edit rejects identifier duplicates with 409 `CONTACT_EXISTS`.
- Uploads: 5 MB cap; decoded UTF-8 (BOM-aware), UTF-16, then cp1252 for Excel-saved CSVs.
- Delete person: hard-deletes memories, interactions, triggers, suggestions, goal_contacts, drafts; sets `contacts.deleted_at` (purge job Sprint 8).
- People list: keyset pagination on (lower(full_name), id), 50 per page, `ilike` search on name/company (trigram index exists for later fuzzy search).
- Person page history = interactions + a synthetic "Added from …" entry; next-step card shows the goal label until the engine (Sprint 4) fills the stage.
- Web: shared `ImportPanel` (onboarding step 2 and People → Add people); Contact Picker wrapped in `lib/device/contactPicker.ts` with .vcf fallback; LinkedIn "Remind me later" remembered in localStorage; note sheet on `<dialog>`; Draft/Voice tiles disabled until Sprints 3/5.

Sprint 1:

- Auth: Supabase access tokens verified in the API via the project JWKS (ES256), HS256 secret as fallback; 401 envelope for missing/invalid/expired tokens.
- `user_session()` runs each request as `authenticated` with the JWT claims (RLS); `service_session()` for server-only tables (events).
- Profile row created on the first authenticated request (insert … on conflict do nothing), no DB trigger.
- New migration `20261025010000_privacy_notice_ack.sql`: `profiles.privacy_notice_version/_ack_at` (user-editable via API). Goal creation requires the current notice version (403 `PRIVACY_NOTICE_REQUIRED`).
- Consents: append-only rows; withdrawing sets `withdrawn_at`. Boxes start unticked (DPDP opt-in). `signup` analytics event fires at first notice acceptance; all events need analytics consent.
- Goal params validated with jsonschema against the pack's `goal_schema` (defaults applied, strings trimmed, empty chips dropped, `uri` format checked); `starts_on` = user's local date, `ends_on` = + pack `duration_days`; second active goal → 409 `GOAL_ALREADY_ACTIVE`.
- Web: supabase-js (PKCE, session persisted) for sign-in only; API client adds the bearer token; route gates: signed out → `/sign-in`; notice not accepted → consents; then resume `onboarding_step`. Steps 2–3 are "Skip for now" placeholders until Sprints 2–3. Referral stepper bounds read from the pack schema.
- `next.config.ts` loads the repo-root `.env` (`@next/env`).
- CI E2E job runs on manual dispatch only while testing is deferred.

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

- API warms one DB connection at startup (`warm_db_pool`); startup continues with a warning if the DB is down.

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

- **WhatsApp go-live:** Meta Business verification, a WhatsApp Cloud API app + number, a permanent system-user token, and the 3 templates above approved. Then set `WA_GRAPH_VERSION`, `WA_PHONE_NUMBER_ID`, `WA_BUSINESS_ACCOUNT_ID`, `WA_ACCESS_TOKEN`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, `WA_DISPLAY_NUMBER` and point the webhook to `<API_BASE_URL>/v1/webhooks/whatsapp` (needs a public HTTPS API, i.e. a deployed staging API or a tunnel).

- **Supabase Auth setup (needed to sign in):** Authentication → URL Configuration: Site URL `http://localhost:3000`, Redirect URLs `http://localhost:3000/auth/callback` (+ production later). Providers → Google: enable with a Google Cloud OAuth client (redirect URI shown on that page). Email templates → Magic Link: add `{{ .Token }}` so the email shows the 6-digit code (the link also works).

- GitHub repo URL needed to add the remote, push `main` + `sprint-0/foundations` and open the Sprint 0 PR (CI's first run).
- **Before beta:** create staging/production Supabase projects in **ap-south-1 (Mumbai)**; the Seoul dev project is for dev only (ADR-0009).
- Turn the Data API off in the dev project dashboard (ADR-0007); the anon revoke already blocks reads.
- Upgrade the Supabase CLI (2.31.8 installed, 2.122 available): `scoop update supabase`.
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

- 25 Oct 2026 — Sprint 6 built: WhatsApp client with recipient guard + dry run, linking, signed webhook with dedupe, commands, notes/voice/contacts capture, show drafts/snooze, daily brief; Settings WhatsApp card. Live smoke (dry run) passed incl. STOP/START, unlinked-sender silence, free vs paid brief.

- 25 Oct 2026 — Sprint 5 built: voice/text capture with signed upload, transcription, audio deletion + audit, extraction, confirm cards, dated follow-ups, sweeps. Live smoke against Groq + Supabase Storage passed.

- 25 Oct 2026 — Sprint 4 built: relevance, ranking, stage machine, Today, send flow with cap, interactions, reply check-ins, progress, nightly ranking + LLM labelling jobs; UI for Today/Draft send/Replies/Progress. Live smoke found and fixed: company-cap grouping, suggestion-draft body, app-scoped settings, free-plan thank-you date.

- 25 Oct 2026 — Sprint 3 built: Groq provider, AI router, draft pipeline with rules + fact check, free limits, style profile; draft screen, stage chooser, style step, upgrade screen. Live Groq smoke after two prompt fixes: correct script, no false fact-check flags.

- 25 Oct 2026 — Sprint 2 built: imports (picker, vCard, LinkedIn CSV) with dedupe preview + idempotent commit, people list/search/paging, person page, add/edit/delete person, notes. Checks, build, unit tests and live smoke pass.

- 25 Oct 2026 — Pushed to GitHub. Sprint 1 built: auth, RLS sessions, /me, /packs, /goals, /privacy/consents; sign-in (Google + email code), consents, goal, settings screens; onboarding resume. Checks, unit tests, build and live API smoke pass. Testing deferred by founder.

- 25 Oct 2026 — Fixed Docker (WSL service was never registered; reinstalled WSL 2.6.3 from Microsoft's signed MSI). Accepted Seoul dev project. Pushed migration + seed. Warmed the DB pool at API startup (cold TLS connect to Seoul took 3 s and tripped the 2 s health timeout). All checks, unit, integration (20) and E2E (8) green; `pnpm dev` health ok/ok/ok. Removed the unused Supabase MCP config (different Supabase account).
- 25 Oct 2026 — Switched to Windows + cloud Supabase dev + Groq only (ADR-0009, ADR-0010); found the dev project is in Seoul; Docker backend not available.
- 25 Oct 2026 — Sprint 0 built on the Windows machine (WSL not installed yet): all scope items written; API + web lint/type/unit, build and E2E green; integration tests, Makefile and Supabase pending a WSL/CI run.
- 25 Oct 2026 — Kickoff review; decisions above approved; docs, schema draft, ADR-0007/0008 updated; Sprint 0 started.
- 25 Oct 2026 — Kickoff pack created (docs, ADRs, schema draft, pack config, design reference).
