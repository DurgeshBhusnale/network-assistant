# Prompts for the coding agent

Paste these into your coding agent (Claude Code or similar), **in order**, from the repo root. Wait for each to finish and check the result before sending the next. If the agent asks a question, answer it before moving on.

Tips:
- Start each new sprint in a fresh session so context stays small; the agent re-reads `CLAUDE.md` and `docs/PROGRESS.md`.
- Use plan mode (or ask for a plan) at the start of every sprint, approve it, then let it build.
- Never let it skip the verification prompt at the end of a sprint.
- Slash commands in `.claude/commands/` do the same as the generic prompts: `/start-sprint 2`, `/review-sprint 2`, `/resume`.

---

## Prompt 0 — Orientation (no code)

```
You are starting a new project. Read, in this order: CLAUDE.md, docs/00-CONTEXT.md, docs/01-PRD.md, docs/02-TECH-SPEC.md, docs/03-SPRINT-PLAN.md, docs/04-DESIGN-GUIDE.md, docs/05-AI-PROMPTS-AND-EVALS.md, docs/06-PRIVACY-CHECKLIST.md, docs/schema-draft.sql, packs/career_sprint.json, docs/adr/*, and skim design/screens/*.dc.html.

Do not write any code yet. Reply with:
1. A 10-line summary of the product and the v1 scope in your own words.
2. The product rules you must never break (from CLAUDE.md), restated briefly.
3. Any contradictions, gaps or ambiguities you found across the docs, with a suggested resolution for each.
4. Questions you need me to answer before Sprint 0 (keep it to what truly blocks you).
5. A detailed plan for Sprint 0: files and folders you will create, tools and versions you will choose, dev commands (package scripts), CI jobs, and the tests you will write. Mark anything you're unsure about.
```

## Prompt 1 — Sprint 0: Foundations

```
Plan approved [add any changes/answers here]. Implement Sprint 0 (Foundations) from docs/03-SPRINT-PLAN.md.

Requirements:
- Monorepo layout exactly as tech spec §3. Use pnpm for web, uv for api.
- Convert docs/schema-draft.sql into the first Supabase migration; create supabase/seed.sql that loads packs/career_sprint.json, the three coming-soon packs and the calendar events.
- Implement every item in the Sprint 0 scope list, including the RLS-everywhere test, log redaction, FakeProvider with AI_MODE=fake, design tokens wired into Tailwind, base components, app shell with bottom nav per design/screens/Main.dc.html, PWA manifest + service worker, CI.
- Keep CLAUDE.md "Commands" section accurate for the package scripts you create.
- Work in small commits on branch sprint-0/foundations.
- When done: run pnpm check, pnpm test and pnpm test:int, then update docs/PROGRESS.md (stories ticked, dependencies added with reasons, decisions, anything I must test on my phone).
Stop and ask me if a requirement is unclear rather than guessing product behaviour.
```

## Prompt 2 — Sprint 0 verification (use after every sprint, changing the number)

```
Verify Sprint 0 against docs/03-SPRINT-PLAN.md:
1. Go through every acceptance criterion and every listed test for this sprint. For each, show the evidence (test name and result, or the exact manual step I should do).
2. Run pnpm check, pnpm test, pnpm test:int (and pnpm e2e if the sprint has E2E tests). Paste the summary.
3. Check the Global Definition of Done items.
4. List anything incomplete, any shortcuts you took, and any deviations from the docs (each deviation needs an ADR or a PROGRESS.md note).
5. Give me a short manual test script for my Android phone.
Do not start the next sprint.
```

## Prompt 3 — Sprint 1: Accounts and goal setup

```
Start Sprint 1 (Accounts and goal setup) from docs/03-SPRINT-PLAN.md. First give me a plan: stories in order, files to create/change, endpoints, migrations (if any), tests per story, and questions. Wait for my approval before coding.

Notes:
- Auth is Google + email OTP via Supabase (ADR-0005). Verify JWTs with the project JWKS.
- Implement user_session() so user requests run under RLS (tech spec §5.1) and add cross-user isolation tests for every endpoint.
- Goal params must validate against the pack goal_schema in packs.config; no Career-Sprint-specific branching in engine code (ADR-0006).
- Screens: sign in, consents, Goal (design/screens/Goal.dc.html), Settings basics, onboarding resume.
Branch: sprint-1/accounts-goal. Update docs/PROGRESS.md when done.
```

(Then run Prompt 2 with "Sprint 1".)

## Prompt 4 — Sprint 2: People

```
Start Sprint 2 (People) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- Write the import fixtures listed in the sprint (LinkedIn CSV with preamble, vCard, picker payload) before the parsers, and write table-driven tests first for normalisers and dedupe.
- Phones → E.164 with default region IN; never auto-merge on name alone.
- Import = preview, then commit; commits are idempotent; > 200 rows run in a worker.
- Contact Picker wrapper in lib/device with feature detection and vCard fallback.
- Screens: Import (design/screens/Import.dc.html), People list, Person page (design/screens/Person.dc.html), add person, notes.
Branch: sprint-2/people. Update docs/PROGRESS.md when done.
```

## Prompt 5 — Sprint 3: AI drafting

```
Start Sprint 3 (AI drafting) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- Build the AI router exactly as tech spec §8 (interface, routing table, timeouts, retries, fallback, JSON validation with one repair retry, ai_calls cost logging). Model ids from env only.
- Copy the v1 prompts from docs/05-AI-PROMPTS-AND-EVALS.md into versioned prompt files.
- Draft pipeline with fact check and ask-detection guard (tech spec §8.3). Never send phone numbers or emails to providers.
- billing/limits.py becomes the single gate for free draft limits (3/month in user timezone).
- Draft sheet UI per design/screens/Draft.dc.html with tone chips and warnings.
- Create evals/ with the runner and a starter drafts.jsonl of 10 synthetic cases; I'll add real anonymised cases later.
- Tests use AI_MODE=fake only. Tell me what live keys you need to demo on staging.
Branch: sprint-3/ai-drafting. Update docs/PROGRESS.md when done.
```

## Prompt 6 — Sprint 4: Engine and daily loop

```
Start Sprint 4 (Engine and daily loop) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- engine/ranking.py, engine/stages.py, engine/triggers.py are pure functions. Write the table-driven tests listed in the sprint BEFORE the implementation. Include one test run with a synthetic second pack config (tests/fixtures/packs/) to prove nothing is hard-coded to Career Sprint (ADR-0006).
- Relevance: deterministic company match, then batched LLM labels (tech spec §7.2).
- Nightly ranking per user timezone with an injectable clock; synchronous first ranking after onboarding (< 3 s for 1,000 contacts).
- Send flow uses wa.me links and LinkedIn copy only (ADR-0004); "Sent?" confirmation on return; daily send cap.
- Screens: Today (Main.dc.html), Did they reply? (Replies.dc.html), Progress (Progress.dc.html), empty states, badges.
Branch: sprint-4/engine-loop. Update docs/PROGRESS.md when done.
```

## Prompt 7 — Sprint 5: Capture

```
Start Sprint 5 (Capture) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- Pipeline per tech spec §8.4: signed upload → worker → STT routing → extract_people.v1 → matching → candidates → confirm. Delete audio immediately after transcription with an audit row, plus an hourly sweep.
- Relative date resolution tests with frozen time in Asia/Kolkata.
- Check the voice consent before recording and in the API.
- Build a small script to run the 20-note language test (Whisper vs Sarvam) on files I provide in a local folder outside git; output a comparison table so we can write the ADR.
- Screen: Capture (design/screens/Capture.dc.html) with processing status and confirm cards; voice memory from the Person page.
Branch: sprint-5/capture. Update docs/PROGRESS.md when done.
```

## Prompt 8 — Sprint 6: WhatsApp assistant

```
Start Sprint 6 (WhatsApp assistant) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- Meta WhatsApp Cloud API direct (tech spec §9). Verify X-Hub-Signature-256 on every webhook, respond fast, process in a worker, dedupe by message id.
- Record webhook fixtures for every inbound type listed in the sprint, each with valid and invalid signatures.
- Add a guard in the WhatsApp client that raises if the recipient isn't the account's verified wa_phone_e164; test it.
- 24-hour window helper; templates only outside the window; daily brief only for paying, opted-in, not opted-out users; STOP stops everything immediately.
- Never store message bodies.
- Tell me exactly which template texts to submit to Meta and which env vars to fill for the staging test number.
- Conversation design: design/screens/WhatsApp.dc.html.
Branch: sprint-6/whatsapp. Update docs/PROGRESS.md when done.
```

## Prompt 9 — Sprint 7: Billing and notifications

```
Start Sprint 7 (Billing and notifications) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- Razorpay per tech spec §10: orders, checkout, webhook signature verification, idempotent events. Grant entitlements ONLY from verified webhooks.
- billing/limits.py gates drafts, model tier, digest cadence and WhatsApp brief eligibility; add a limits-matrix test (free/sprint/pro × each action).
- Upgrade screen per design/screens/Upgrade.dc.html; prices from config, GST-inclusive.
- Web push (VAPID) and Resend email digest with one-click unsubscribe.
- Pro and the price test are behind PRO_ENABLED / PRICE_TEST_ENABLED flags.
Branch: sprint-7/billing. Update docs/PROGRESS.md when done.
```

## Prompt 10 — Sprint 8: Privacy, analytics, hardening

```
Start Sprint 8 (Privacy, analytics, hardening) from docs/03-SPRINT-PLAN.md. Plan first and wait for approval.

Notes:
- Export and delete-account workers per tech spec §12; the delete test must iterate over every user-owned table.
- Consent management UI; withdrawing consent disables the feature (test it).
- Audit analytics events against tech spec §13 and fill gaps; owner-only admin metrics page.
- Performance and accessibility passes (Lighthouse CI budgets, axe in Playwright), security review (headers, CSP, rate limits, dependency audit, PII-in-logs test).
- Finish with the beta launch checklist from the sprint plan, marking each item done or listing what I must do.
Branch: sprint-8/hardening. Update docs/PROGRESS.md when done.
```

---

## Utility prompts

**Resume after a break**
```
Read CLAUDE.md and docs/PROGRESS.md. Tell me where we are, what's next, and any open questions. Then continue with the next unticked story in the current sprint, following the plan already approved.
```

**Fix CI**
```
CI is failing. Reproduce locally, find the root cause, and fix the code. Do not skip, weaken or delete tests unless you show me why the test itself is wrong and I agree. Summarise the cause and the fix.
```

**Change of plan**
```
I want to change [describe]. Before coding: tell me which docs, requirements (FR IDs), ADRs, tables, endpoints and tests this affects, and propose the doc updates (including a new ADR if it changes a decision). Wait for my OK.
```

**Design updated**
```
I've updated design/screens/[file]. Compare it with the current implementation of that screen, list the differences, then update the component to match. Keep using tokens; if new tokens are needed, add them to design/tokens.css and the Tailwind theme.
```

**Security and privacy review (before beta)**
```
Do a security and privacy review of the whole repo against CLAUDE.md, docs/06-PRIVACY-CHECKLIST.md and tech spec §12. Check: RLS on every table and isolation tests, unscoped service-role queries, webhook signature checks, secrets in code or logs, PII in logs and AI prompts, consent checks, rate limits, CSP/headers. Report findings ranked by severity with file and line, then fix the high-severity ones after I confirm.
```
