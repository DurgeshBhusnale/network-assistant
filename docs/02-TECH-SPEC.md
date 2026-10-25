# Technical Specification — Networking Assistant (v1)

| | |
|---|---|
| Status | Draft v1.0, 25 Oct 2026 |
| Implements | `01-PRD.md` (requirement IDs like FR-CON-3 are referenced below) |
| Decisions log | `docs/adr/` — change a decision by adding an ADR, not by silently diverging |

---

## 1. Architecture

```
            ┌──────────────┐      REST (JWT)      ┌──────────────────┐      ┌───────────────────────┐
 User ───▶  │ Web app (PWA)│ ───────────────────▶ │ API (FastAPI)    │ ───▶ │ Supabase Postgres     │
 (Android   │ Next.js      │                      │ /v1/*            │      │ (+pgvector, RLS,      │
  first)    └──────────────┘                      │ webhooks         │      │  Auth, Storage)       │
    │                                             └───────┬──────────┘      │ region: ap-south-1    │
    │  WhatsApp app                                       │ enqueue          └───────────────────────┘
    └──────────────▶ Meta WhatsApp Cloud API ──webhook──▶ │                           ▲
                         ▲                         ┌──────▼──────────┐                │
                         └─────── send ─────────── │ Workers (arq)   │ ───────────────┘
                                                   │ ranking, media, │ ───▶ AI router ─▶ Groq
 Razorpay ──────────────webhook──────────────────▶ │ briefs, digests │
                                                   └─────────────────┘   Redis (queue + rate limits)
```

- **One backend** (Python) serves both front doors (web app and WhatsApp). Heavy or slow work runs in background workers.
- **Frontend never queries tables directly.** It uses Supabase only for authentication; all data flows through the API. The Supabase Data API is disabled (ADR-0007).
- The web app calls the API on its own origin (`/api/v1/*`); Next.js rewrites forward to the API. One origin for the phone, no CORS.
- **All AI calls go through one AI router module** (`apps/api/app/ai/`), never directly from product code.

## 2. Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js (App Router), TypeScript (strict), Tailwind CSS v4 with CSS-variable design tokens mapped via `@theme inline` | Installable PWA (manifest + hand-written service worker), Android Chrome first |
| Frontend data | TanStack Query; generated API client from FastAPI OpenAPI (`openapi-typescript`) | No hand-written fetch types |
| Backend API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + asyncpg | `uv` for dependency management |
| Workers | `arq` (Redis-backed, asyncio, cron support) | Same codebase as API (`apps/api`) |
| Database | Supabase Postgres + pgvector, migrations via Supabase CLI (`supabase/migrations`) | Mumbai region `ap-south-1` |
| Auth | Supabase Auth: Google OAuth + email OTP | Phone is verified via WhatsApp linking, not SMS (ADR-0005) |
| File storage | Supabase Storage, private bucket `captures` (audio, short-lived) | Signed upload URLs |
| AI | Groq only in v1 (ADR-0010): gpt-oss-20B, gpt-oss-120B, Whisper Large v3 Turbo / Large v3 | Model IDs in env, never hard-coded |
| Messaging | Meta WhatsApp Cloud API (direct, no BSP), Web Push (VAPID), email via Resend (or SES ap-south-1) | |
| Payments | Razorpay (Orders + Checkout + webhooks); Cashfree as alternative | UPI first |
| Observability | Sentry (web + api), structured JSON logs with PII redaction | |
| Testing | pytest + pytest-asyncio, httpx; Vitest + React Testing Library; Playwright (mobile emulation) | |
| Lint/format | ruff (lint + format), mypy (strict on `engine/`, `billing/`, `ai/`); ESLint, Prettier, `tsc --noEmit` | |
| Hosting | Web: Vercel (region `bom1`). API + workers: a host with a Mumbai region (e.g., Fly.io `bom` or AWS `ap-south-1`). Redis: managed, in/near Mumbai | Confirm regions at setup |

Pin exact versions in lockfiles (`pnpm-lock.yaml`, `uv.lock`). Use the latest stable versions at project start.

## 3. Repository layout (monorepo)

```
/
├─ CLAUDE.md                 # agent rules (read first)
├─ README.md
├─ docs/                     # PRD, tech spec, sprint plan, design guide, AI prompts, ADRs, PROGRESS.md
├─ design/                   # tokens.css, screen reference markup from the design canvas
├─ apps/
│  ├─ web/                   # Next.js PWA
│  │  ├─ app/                # routes: (auth), onboarding, today, people, person/[id], capture, replies, progress, upgrade, settings
│  │  ├─ components/         # UI kit built on design tokens
│  │  ├─ lib/api/            # generated client + query hooks
│  │  ├─ lib/device/         # contact picker, recorder, share/wa.me helpers
│  │  ├─ public/             # manifest.webmanifest, icons, sw.js
│  │  └─ e2e/                # Playwright tests
│  └─ api/
│     ├─ app/
│     │  ├─ main.py          # FastAPI app factory
│     │  ├─ core/            # config, db session, auth (JWT), rate limits, logging, errors
│     │  ├─ api/v1/          # routers (one file per resource)
│     │  ├─ domain/          # models (SQLAlchemy), schemas (Pydantic)
│     │  ├─ engine/          # packs, ranking, stages, triggers — pure, unit-testable
│     │  ├─ ai/              # router, providers/, prompts/ (versioned), factcheck, fake/fixtures/ (AI_MODE=fake)
│     │  ├─ imports/         # vcard, linkedin_csv, picker, dedupe, normalise
│     │  ├─ capture/         # transcription + extraction pipeline
│     │  ├─ channels/        # whatsapp/, push/, email/
│     │  ├─ billing/         # razorpay, entitlements, limits
│     │  ├─ privacy/         # consents, export, delete, audit
│     │  ├─ analytics/       # event tracking
│     │  └─ workers/         # arq settings, tasks, cron
│     └─ tests/              # unit/, integration/, fixtures/ (webhook payloads, CSV/VCF samples)
├─ packs/                    # pack configs (career_sprint.json, coming_soon.json, calendar_events.json) → supabase/seed.sql via apps/api/scripts/build_seed.py
├─ evals/                    # draft/extraction golden sets + runner
├─ supabase/                 # config.toml, migrations/, seed.sql
├─ docker-compose.yml        # local Redis
├─ .env.example
└─ .github/workflows/ci.yml
```

## 4. Environments and configuration

| Env | Purpose | Data |
|---|---|---|
| local | Development (Windows or Linux) | Cloud Supabase **dev** project (ADR-0009) + Redis; `AI_MODE=fake` by default. CI uses a throwaway Supabase CLI stack |
| staging | Beta testing, webhook testing | Separate Supabase project, WhatsApp test number, Razorpay test mode |
| production | Users | Supabase Mumbai, live keys |

All config via environment variables (see `.env.example`), loaded by `app/core/config.py` (pydantic-settings). **Never commit secrets.** `AI_MODE=fake` makes every provider return deterministic fixtures (`app/ai/fake/fixtures/`) so tests and local dev never call paid APIs.

## 5. Data model

Full DDL: `supabase/migrations/20261025000000_init_schema.sql` (mirrored in `docs/schema-draft.sql`). Summary:

| Table | Purpose / key fields |
|---|---|
| `profiles` | 1:1 with `auth.users`. User-editable: display_name, language, timezone, nudge_time, onboarding_step. Server-managed (ADR-0007): wa_phone_e164, wa_opt_in_at, wa_opt_out_at, wa_last_inbound_at, price_cohort, utm. Plan is computed from `entitlements` by `billing/limits.py` (no cached column) |
| `packs` | id (text, e.g. `career_sprint`), name, status (`active`/`coming_soon`), config jsonb (see §7.1) |
| `goals` | user_id, pack_id, params jsonb, status (`active`/`paused`/`done`), starts_on, ends_on |
| `contacts` | user_id, full_name, first/last, phones text[] (E.164), emails text[], linkedin_url, company, company_norm, title, city, how_known, birthday (date), sources text[], last_interaction_at, deleted_at |
| `memories` | contact_id, user_id, text, source (`note`/`voice`/`whatsapp`/`import`), embedding vector(384) nullable (P1), created_at |
| `goal_contacts` | goal_id, contact_id, relevance_label, relevance, state (`none`/`warmed`/`asked`/`replied`/`won`), outcome (pack outcome, e.g. `referred`), last_suggested_at, last_sent_at, thanked_at, dismissed_at |
| `suggestions` | user_id, goal_id (nullable for stay-in-touch), contact_id, for_date, score, reasons jsonb, stage (pack stage id: `warm_up`/`ask`/`follow_up`/`thank`), status (`pending`/`opened`/`sent`/`snoozed`/`dismissed`/`expired`), snoozed_until |
| `drafts` | suggestion_id, user_id, contact_id, stage, tone, language, provider, model, prompt_version, text, final_text, regenerations, factcheck jsonb, sent_channel, send_opened_at (daily cap), sent_at |
| `interactions` | user_id, contact_id, goal_id, type (`met`/`sent`/`replied`/`no_reply`/`note`/`outcome`), stage (for `sent`), outcome (for `outcome`), channel, occurred_at, meta jsonb |
| `style_profiles` | user_id, samples text[] (max 10), summary text, updated_at |
| `triggers` | user_id, contact_id, type (`birthday`/`festival`/`met_recently`/`job_change`), date |
| `calendar_events` | date, name, kind (`festival`), active — admin-seeded (e.g., Diwali 8 Nov 2026, New Year) |
| `imports` | user_id, source (`picker`/`vcard`/`linkedin_csv`/`manual`), status, counts jsonb, errors jsonb |
| `captures` | user_id, source (`app_audio`/`app_text`/`wa_audio`/`wa_text`), storage_path / wa_media_id, language, transcript (cleared on confirm/discard or after 24 h), extracted jsonb, status, audio_deleted_at |
| `wa_link_codes` | user_id, code (6 chars), expires_at, used_at |
| `wa_messages` | user_id, direction, kind (`template`/`text`/`interactive`/`audio`), template_name, wa_message_id, status, created_at — **no message bodies stored** |
| `entitlements` | user_id, product (`sprint`/`pro`), starts_at, ends_at, drafts_used, source_payment_id |
| `payments` | user_id (nullable, `on delete set null`: kept anonymised for tax), provider, product, amount_paise, currency, status, provider_order_id, provider_payment_id, raw_event_id |
| `consents` | user_id, type (`contacts`/`voice`/`whatsapp`/`analytics`), version, granted_at, withdrawn_at |
| `events` | user_id, name, props jsonb, occurred_at (analytics) |
| `ai_calls` | user_id, task, provider, model, prompt_version, tokens_in, tokens_out, audio_seconds, cost_inr, latency_ms, ok, created_at |
| `push_subscriptions` | user_id, endpoint, keys jsonb |
| `audit_log` | user_id, action (`export`/`delete_account`/`audio_deleted`/`consent_change`), meta, created_at |

Rules:
- Every user-owned table has `user_id uuid not null references auth.users on delete cascade` and an index on `user_id` (exception: `payments`, see above).
- Soft delete only for `contacts` (`deleted_at`), purged after 30 days; deleting a contact hard-deletes its memories, interactions, suggestions, goal_contacts, triggers and drafts immediately. Everything else hard-deletes.
- Stages, states and outcomes are text validated against the pack config (ADR-0008); only generic values have DB checks.
- Money in paise (integers). Times in `timestamptz` (UTC); dates for a user's local day are computed with their timezone.

### 5.1 Row-level security

- Supabase Data API **off** (local `config.toml` and hosted dashboard); `anon` has no privileges on any table; `authenticated` can only write user-editable `profiles` columns (ADR-0007).
- RLS **enabled on every table**. Policy pattern: `user_id = auth.uid()` for select/insert/update/delete. `packs` and `calendar_events` are read-only to authenticated users.
- The API executes per-request queries as the user: inside a transaction it runs `set local role authenticated; select set_config('request.jwt.claims', '<claims json>', true);` so RLS applies (helper: `core/db.py::user_session(claims)`).
- Workers and webhooks use a service connection (bypasses RLS) and **must** scope every query by `user_id` explicitly. Code review rule: no unscoped queries on user tables.

## 6. API (v1)

Base path `/v1`. JSON. Auth: `Authorization: Bearer <Supabase access token>`, verified against the project's JWKS (or legacy JWT secret). Errors: `{"error": {"code": "...", "message": "..."}}` with stable codes (e.g., `SEND_CAP_REACHED`, `FREE_LIMIT_REACHED`, `NOT_FOUND`).

| Method & path | Purpose | PRD |
|---|---|---|
| `GET /health` | Liveness + DB/Redis check | — |
| `GET /me` · `PATCH /me` | Profile, language, timezone, nudge time, onboarding step | FR-AUTH-3 |
| `GET /packs` | Pack list with status | FR-GOAL-1 |
| `POST /goals` · `GET /goals/active` · `PATCH /goals/{id}` | Create/read/update goal; creating triggers relevance labelling + first ranking | FR-GOAL-* |
| `POST /imports/picker` | JSON array from Contact Picker → preview | FR-CON-1 |
| `POST /imports/file` | Multipart `.vcf` or `.csv` → preview | FR-CON-2/3 |
| `GET /imports/{id}` · `POST /imports/{id}/commit` | Preview counts + commit | FR-CON-5/7 |
| `GET /contacts?q=&cursor=` · `POST /contacts` | List/search, create | FR-CON-4/8 |
| `GET /contacts/{id}` · `PATCH` · `DELETE` | Person page data (contact + memories + timeline + next step) | FR-PER-*, FR-CON-9 |
| `POST /contacts/{id}/memories` · `DELETE /memories/{id}` | Notes | FR-MEM-1 |
| `POST /captures/upload-url` | Signed URL for audio upload | FR-MEM-2 |
| `POST /captures` | Start capture from `storage_path` or `text` → job | FR-MEM-2/6 |
| `GET /captures/{id}` | Status + candidates (people, facts, follow-up, merge suggestions) | FR-MEM-3 |
| `POST /captures/{id}/confirm` | Apply user decisions per candidate | FR-MEM-3/4 |
| `GET /today` | Suggestions for the user's local today + goal strip | FR-TODAY-* |
| `POST /suggestions/{id}/snooze` · `/dismiss` | | FR-TODAY-2 |
| `POST /suggestions/{id}/draft` | Generate draft for a Today suggestion (checks entitlement/limits) | FR-DRAFT-1 |
| `POST /contacts/{id}/draft` | Body `{stage}`; draft from the Person page (no suggestion) | FR-PER-2 |
| `POST /drafts/{id}/regenerate` | Body `{tone}`. Not a new draft for limits; free users max 3 per draft | FR-DRAFT-2 |
| `PATCH /drafts/{id}` | Save edited `final_text` | FR-DRAFT-6 |
| `POST /drafts/{id}/send` | Body `{channel: "whatsapp"\|"linkedin"}` → checks send cap, returns `{open_url, copy_text}`; the first call per draft sets `send_opened_at` and counts toward the daily cap; records `sent` only after confirm | FR-SEND-* |
| `POST /interactions` | Log `sent`/`replied`/`no_reply`/`referred`/`interview` | FR-SEND-4, FR-REP-* |
| `GET /replies/pending` | People messaged 2–5 days ago without a logged outcome | FR-REP-1 |
| `GET /progress` | North star, funnel, by-company | FR-PROG-1 |
| `PUT /style/samples` | Up to 10 sample messages → regenerate style summary | FR-ONB-1 |
| `POST /whatsapp/link-code` | Create 6-char code + `wa.me` URL | FR-WA-1 |
| `GET /webhooks/whatsapp` · `POST /webhooks/whatsapp` | Meta verify + inbound events | FR-WA-* |
| `POST /billing/orders` | Create Razorpay order for product | FR-PAY-4 |
| `GET /billing/entitlement` | Current plan, limits, usage | FR-PAY-* |
| `POST /webhooks/razorpay` | Payment events | FR-PAY-4 |
| `POST /push/subscribe` · `DELETE /push/subscribe` | Web push | FR-NOT-1 |
| `GET /privacy/consents` · `PUT /privacy/consents` | | FR-PRIV-1 |
| `POST /privacy/export` · `POST /privacy/delete-account` | Async jobs; export link emailed/shown | FR-PRIV-2/3 |
| `GET /admin/metrics` | Owner only (`ADMIN_USER_IDS`) | FR-AN-2 |

Rate limits (Redis): 60 req/min/user general; drafts 20/min/user; imports 5/hour/user; webhooks unlimited but signature-checked.

## 7. Engine

All engine code is **pure functions over plain data** in `app/engine/`, fully unit tested, no I/O.

### 7.1 Pack configuration

Packs live in `packs/*.json`, seeded into `packs.config`. See `packs/career_sprint.json`. Shape:

```jsonc
{
  "id": "career_sprint", "name": "Career Sprint", "status": "active", "duration_days": 60,
  "goal_schema": { /* JSON Schema for goals.params */ },
  "relevance": { "weights": { "target_company": 1.0, "same_field": 0.6, "can_introduce": 0.3, "not_relevant": 0.1 } },
  "stages": [ { "id": "warm_up", "has_ask": false }, { "id": "ask", "has_ask": true }, { "id": "thank", "has_ask": false } ],
  "outcomes": ["referred", "interview"],
  "timing_boosts": { "birthday": 1.5, "festival": 1.5, "met_recently": 1.3, "met_recently_days": 7, "job_change": 1.2 },
  "daily_list": { "min": 3, "max": 7, "default": 5, "max_per_company": 2 },
  "prompts": { "relevance": "career_sprint.relevance.v1", "draft": "career_sprint.draft.v1" }
}
```

### 7.2 Relevance labelling

On goal create/update and after each import commit: for each contact, deterministic pass first, then LLM for the rest.
1. `company_norm` fuzzy-matches (rapidfuzz `token_set_ratio ≥ 90`) a target company → `target_company`.
2. Otherwise batch contacts (50 per call) to the `relevance` prompt with title, company, how_known, latest 3 memories → label ∈ {`same_field`, `can_introduce`, `not_relevant`} + one-line reason.
3. Store in `goal_contacts.relevance_label` / `relevance`. Re-label only changed contacts.

### 7.3 Ranking (nightly + on demand)

```
score = R × W × T × E × (1 − F)
```

| Factor | Definition (v1 defaults, tune in beta) |
|---|---|
| R relevance | From pack weights by label (1.0 / 0.6 / 0.3 / 0.1) |
| W warmth | `clamp(0.2 + 0.15·min(n_interactions, 4) + recency, 0.2, 1.0)`; recency = 0.2 if last interaction < 90 days, 0.1 if < 365 days, else 0. `met` and `replied` count double |
| T timing | Product of applicable boosts: birthday today 1.5, festival today 1.5, met in last 7 days 1.3, job change in last 30 days 1.2; else 1.0 |
| E ease | 1.0 has phone; 0.8 LinkedIn URL only; 0.5 neither |
| F fatigue | 1.0 if asked in last 30 days, or snoozed (until date), or dismissed for this goal; 0.5 if any message in last 7 days; else 0. Thank-you and dated follow-up suggestions skip fatigue |

Selection: sort by score desc, take up to `daily_list.default` with ≤ `max_per_company` per normalised company, skip score 0. Add dated follow-ups from captures first (they always appear on their date). Reasons: top 1–3 human-readable strings from contributing factors (e.g., "Works at Razorpay", "Birthday today", "Met 3 days ago", "Replied to you in May").

**State machine per (goal, contact)** (ADR-0008): state `none → warmed → asked → replied → won`; `won` carries the pack outcome (`referred`/`interview`); a sent thank-you sets `thanked_at`.
- Suggest stage `warm_up` when state is `none` and W < 0.6. Suggest `ask` when state is `warmed` and ≥ 3 days since warm-up, or state is `none` and W ≥ 0.6. Suggest `thank` when state is `won` and `thanked_at` is null. A `no_reply` after ask → fatigue 30 days, then one gentle follow-up (stage `follow_up`) allowed.

Nightly job runs at 02:00 in each user's timezone (batch by timezone) and writes `suggestions` for that local date; marks yesterday's unsent suggestions `expired`. Free users: ranking runs weekly (Sunday night) and the list persists all week.

### 7.4 Triggers

Daily job builds `triggers` for the next 7 days: birthdays (from `contacts.birthday`), festivals (from `calendar_events`), met-recently (from `interactions.type='met'`). Job changes: when an import updates a contact's company, record `job_change`.

## 8. AI layer

### 8.1 Router interface

```python
class AIRouter:
    async def extract_people(self, text: str, *, user_id, language) -> ExtractResult
    async def label_relevance(self, contacts: list[ContactBrief], goal: GoalBrief, *, user_id) -> list[RelevanceLabel]
    async def draft(self, req: DraftRequest, *, user_id, tier: Tier) -> DraftResult
    async def factcheck(self, draft: str, facts: list[str], *, user_id) -> FactCheckResult
    async def summarise_style(self, samples: list[str], *, user_id) -> str
    async def transcribe(self, audio: bytes, mime: str, *, user_id, language_hint) -> Transcript
```

- Every call: timeout (LLM 20 s, STT 60 s), 1 retry on 5xx/timeout with jitter, then fallback provider, structured output validated with Pydantic (one repair retry on invalid JSON), cost + latency logged to `ai_calls`.
- `AI_MODE=fake` → `FakeProvider` returning fixtures from `app/ai/fake/fixtures/`.
- Every prompt input passes through the PII scrubber (phones, emails; same patterns as the log redactor) before it reaches a provider. Tested.
- Prompts are versioned files in `app/ai/prompts/<name>.v<N>.md`; `prompt_version` stored on outputs. Text of v1 prompts: `docs/05-AI-PROMPTS-AND-EVALS.md`.

### 8.2 Model routing

| Task | Primary | Fallback | Notes |
|---|---|---|---|
| extract_people, label_relevance, factcheck, summarise_style | Groq `openai/gpt-oss-20b` (`MODEL_SMALL`) | Groq `openai/gpt-oss-120b` (`MODEL_FALLBACK_SMALL`) | JSON output; batch where possible |
| draft (all tiers and stages) | Groq `openai/gpt-oss-120b` (`MODEL_DRAFT`) | Groq `openai/gpt-oss-20b` (`MODEL_FALLBACK_DRAFT`) | Paid vs free differs in limits, not models |
| transcribe (all languages) | Groq `whisper-large-v3-turbo` (`MODEL_STT`) | Groq `whisper-large-v3` (`MODEL_STT_FALLBACK`) | Hindi/Marathi/Hinglish quality checked in Sprint 5 |

Groq only (ADR-0010): "fallback" is a second Groq model, so a full Groq outage degrades AI features (drafts show a retry message). Adding another approved provider later is config + one provider file.

Model IDs come from env (`MODEL_*`). Provider data rule: in v1 only Groq receives user data (approved list: Groq, Anthropic, Sarvam, OpenAI STT); no DeepSeek first-party API; send only fields the task needs (no phone numbers or emails in prompts).

### 8.3 Drafting pipeline

1. Build `DraftRequest`: pack + stage, goal params (incl. a matching `job_links` entry for the contact's company, if any), contact brief (name, title, company, how_known), up to 20 most recent memories, last 3 interactions, style summary + 3 samples, language, tone.
2. Generate with routed model.
3. Fact check: `factcheck` returns unsupported claims. If any → regenerate once with the claims listed as forbidden → if still unsupported, return the draft with `factcheck.warnings` (UI highlights them).
4. Enforce rules in code too: ≤ 90 words; no URLs unless in memories; warm-up drafts fail validation if the ask-detector (keyword + model flag) fires.
5. Store `drafts` row with provider/model/prompt_version; count against entitlement.

### 8.4 Capture pipeline (voice/text, app or WhatsApp)

1. Audio arrives (Storage path from signed upload, or WhatsApp media id).
2. Download (WhatsApp: `GET /{version}/{media-id}` → URL → `GET` with bearer token). Accept `audio/ogg; codecs=opus`, `audio/webm`, `audio/mp4`, `audio/mpeg`, ≤ 16 MB, ≤ 5 min.
3. Language detect (STT result or hint) → route STT → transcript.
4. `extract_people` → `{people: [{name, company, title, where_met, facts[], commitments[], follow_up_date}], unassigned_facts[]}`. Resolve relative dates ("Monday") with the user's timezone and the capture timestamp.
5. Match each person: exact phone/email/LinkedIn; else rapidfuzz on name (+ company) ≥ 85 → "possible match".
6. Save candidates to `captures.extracted`; status `ready`. **Delete audio** (Storage object) immediately after successful transcription; set `audio_deleted_at`; audit log.
7. On confirm: create/merge contacts, add memories, `interactions(type='met')`, triggers/suggestion for follow-up date.
8. On confirm or discard, clear `captures.transcript` (and candidate text in `extracted`). A cron sweep clears unconfirmed captures after 24 h; another deletes leftover audio older than 1 h.

## 9. WhatsApp integration

- **Meta Cloud API direct**, one business number. Graph API version from env (`WA_GRAPH_VERSION`).
- **Webhook verify:** `GET /webhooks/whatsapp` echoes `hub.challenge` when `hub.verify_token == WA_VERIFY_TOKEN`.
- **Webhook security:** verify `X-Hub-Signature-256` = `sha256=` + HMAC-SHA256(raw body, `WA_APP_SECRET`) with constant-time compare; reject otherwise. Respond 200 fast; enqueue processing; dedupe by message id (idempotent).
- **Linking (FR-WA-1):** user taps link → WhatsApp opens with `START ABC123` → webhook matches code (unexpired, unused) → set `profiles.wa_phone_e164`, `wa_opt_in_at`; reply confirmation. Messages from unlinked numbers get one reply with a link to sign up; nothing else.
- **24-hour window:** track `last_inbound_at` per user (from webhooks). Free-form replies only inside 24 h of the user's last message; outside → approved templates only. Code helper `can_send_freeform(user)`.
- **Templates (submit for approval in Sprint 6):**

| Name | Category | Variables | Buttons |
|---|---|---|---|
| `daily_brief_v1` | Utility | first name, 3 lines "Name — reason" | Quick replies: Show drafts, Snooze today |
| `sprint_reminder_v1` | Utility | days left, referrals so far | URL: open app |
| `capture_ready_v1` | Utility | count of people found | URL: review in app |

Keep template text factual so Meta classifies it as utility. No marketing templates in v1.
- **Inbound handling:** `text` → command (START/STOP/HELP/TODAY) or capture; `audio` → capture pipeline; `button`/`interactive` replies → actions (show drafts, snooze, save candidate); `contacts` (shared vCard) → create contact candidate; everything else → help text.
- **STOP:** set `wa_opt_out_at`, stop all outbound immediately, confirm once.
- **Cost guard:** outbound templates only for users with an active paid entitlement and `wa_opt_in_at` set and not opted out.

## 10. Billing and entitlements

- Products (server config): `sprint` ₹799 (79,900 paise) one-time, 60 days, fair-use 400 drafts; `pro_monthly` ₹299; `pro_yearly` ₹2,499. Prices GST-inclusive.
- Flow: `POST /billing/orders` → Razorpay order (receipt = our payment id) → Checkout in web → client returns `razorpay_payment_id`, `razorpay_order_id`, `razorpay_signature` → API verifies HMAC-SHA256(`order_id|payment_id`, key secret) for UX only → **entitlement is granted only from the verified webhook** (`X-Razorpay-Signature` = HMAC-SHA256(raw body, webhook secret); events `payment.captured` / `order.paid`), idempotent by event id.
- Pro (recurring) via Razorpay Subscriptions in Sprint 7 if time allows; otherwise P1 follow-up.
- Free limits: 3 drafts / calendar month (user timezone). Only the first generation of a draft counts; tone changes and "Another version" don't, but free users get at most 3 regenerations per draft (`FREE_REGENERATIONS_PER_DRAFT`). `billing/limits.py` is the single source of truth; every draft endpoint calls it.
- Price test (P1): `profiles.price_cohort` assigned at signup; product price looked up by cohort.

## 11. Notifications

- Web push (VAPID, `pywebpush`) for installed PWA: daily nudge (paid, at nudge_time, if not sent via WhatsApp), weekly digest (free, Monday 09:00 local).
- Email (Resend): weekly digest for free users with one-click unsubscribe; receipts.
- Never include contact phone numbers/emails in notifications; names + reasons only.

## 12. Privacy, security, compliance (DPDP)

India's DPDP obligations on consent, notice and breach reporting apply from May 2027 (a month after launch); build them in now. Checklist lives in `docs/06-PRIVACY-CHECKLIST.md`.

- Consents per §PRD 7.11 stored in `consents` with policy version; features check consent before running (no consent for voice → capture disabled).
- Data location: Supabase `ap-south-1`. Encryption in transit (TLS) and at rest (provider default).
- Secrets only in env/secret manager. Service keys only on the server.
- PII redaction in logs: phones, emails, message text, transcripts never logged; use ids.
- Webhook signature verification (WhatsApp, Razorpay); rate limits on auth-adjacent and send endpoints.
- Export: async job builds a zip (JSON per table + `contacts.csv`), stored 24 h behind a signed URL.
- Delete account: async job deletes all user rows (cascade), Storage objects, push subscriptions, Supabase auth user; writes a minimal audit row (user id hash + timestamp) only.
- Retention jobs (worker cron): purge soft-deleted contacts after 30 days, draft text after 180 days, `wa_messages` after 90 days, `events` and `ai_calls` after 13 months (Sprint 8); clear unconfirmed capture text after 24 h and leftover audio after 1 h (Sprint 5).
- Breach runbook (`docs/06-PRIVACY-CHECKLIST.md`): report within 72 hours.
- Open legal question: notice/basis for storing contacts' data — lawyer review before public launch.

## 13. Analytics

Server-side `events` table via `analytics.track(user_id, name, props)`. Names (snake_case):

`signup`, `goal_created`, `contacts_imported` {source, count, duplicates}, `suggestion_shown` {stage, score}, `suggestion_opened`, `draft_generated` {model, prompt_version, latency_ms, tier}, `draft_regenerated` {tone}, `draft_sent` {channel, edit_ratio}, `reply_logged` {days_to_reply, stage}, `outcome_logged` {type}, `voice_captured` {language, people_found, confirmed}, `wa_linked`, `checkout_started` {product, price}, `payment_succeeded` {product, price}, `sprint_completed`, `pro_upgraded`, `account_deleted`.

`edit_ratio` = normalised Levenshtein distance between draft text and final text. Acquisition: UTM params captured at signup into `profiles.utm` (jsonb).

## 14. Non-functional requirements

| Area | Target |
|---|---|
| Performance | `GET /today` p95 < 300 ms; draft generation p95 < 6 s (Groq path); capture to candidates p95 < 25 s for a 1-min note; import 1,000 contacts < 30 s |
| Frontend | Lighthouse mobile: Performance ≥ 85, PWA installable, Accessibility ≥ 95; first load JS < 200 kB gzipped on Today |
| Availability | Beta: best effort; health checks + Sentry alerts |
| Cost | AI + WhatsApp ≤ ₹60 per Sprint user per month; free user ≤ ₹4/month (monitor via `ai_calls`) |
| Accessibility | Touch targets ≥ 44 px; text contrast ≥ 4.5:1; real buttons/links/labels; works with TalkBack |
| i18n | UI strings in English v1 via a message catalogue (`next-intl`-ready); drafts in English/Hinglish/Hindi/Marathi |

## 15. Testing strategy

| Level | Tooling | Scope | Gate |
|---|---|---|---|
| Unit | pytest, Vitest | engine (ranking, stages, triggers), imports (parsers, normalisers, dedupe), billing limits, AI output validators, UI components | CI, every PR |
| Integration | pytest + local Supabase + Redis | API routes with RLS (user A cannot read user B), workers, webhooks with recorded fixtures and real signature checks | CI, every PR |
| Contract | pytest | WhatsApp/Razorpay payload fixtures (inbound text, audio, button reply, status; payment.captured) | CI |
| E2E | Playwright, Pixel 7 emulation | Onboarding, import, draft→send, capture→confirm, reply logging, upgrade (Razorpay test mode stub) | CI on every PR and main while the suite runs < 5 min (then main only); before each sprint sign-off |
| Evals | `evals/` runner (manual / nightly) | Draft quality (factuality, length, ask rules, tone), extraction accuracy | Before changing prompts or models |
| Manual | Real Android phone | Contact Picker, install, voice recording, wa.me opening, WhatsApp test number | Each sprint demo |

Coverage targets: `engine/`, `billing/`, `imports/` ≥ 90% lines; overall API ≥ 75%; web ≥ 60%. No live AI/WhatsApp/Razorpay calls in CI.

## 16. Deployment and CI

- GitHub Actions: lint + typecheck + unit + integration (services: postgres via Supabase CLI, redis) + contract (generated OpenAPI client and seed in sync) + E2E on PRs and `main`.
- Migrations: `supabase db push` in deploy pipeline; migrations are forward-only and reviewed.
- Web: Vercel preview per PR; production on `main` tag. API/workers: container image, deploy on tag.
- Feature flags: simple `feature_flags` env/JSON (`WA_BRIEFS_ENABLED`, `PRO_ENABLED`, `PRICE_TEST_ENABLED`).
