# Product Requirements Document — Networking Assistant (v1)

| | |
|---|---|
| Status | Draft v1.0, 25 Oct 2026 |
| Owner | Durgesh (founder) |
| Working name | `[App name]`: name not decided; use the placeholder everywhere in UI copy |
| Related | `02-TECH-SPEC.md`, `03-SPRINT-PLAN.md`, `04-DESIGN-GUIDE.md`, research reports 1–5 (project docs) |

---

## 1. Summary

An AI relationship assistant that turns the people a user **already knows** into the outcome they want. It remembers who they met and what was said, picks who to contact each day, drafts the message in the user's own voice, and tracks what happened.

v1 ships **one goal pack, the Career Sprint** (get job referrals through your own network), built on a **general relationship engine**: capture → remember → rank → draft → track. Later goal packs (freelance clients, event follow-up, sales, fundraising, hiring, outsourcing and vendors, alumni communities) reuse the same engine with new configuration. **Build the engine generic and the pack as data.**

## 2. Problem

Working professionals meet valuable people, intend to stay in touch, and don't. Following up needs memory, context and energy at exactly the moment they have none.

Where follow-up breaks (from Report 1):

| Step | What happens | Where it breaks |
|---|---|---|
| 1. Capture | Saves a name and number at an event | No context saved |
| 2. Recall | Weeks later: who was this, why do they matter? | Memory fades |
| 3. Trigger | Birthday, their post, a job change, own job search | "I'll do it tonight" |
| 4. Act | Writing a non-awkward message after months of silence | No energy, guilt |

Existing tools (Dex, Mesh/ex-Clay, Covve, Monica) mostly fix steps 1 and 3 with reminders and manual data entry. **v1 must fix steps 2 and 4: recall and action.**

Evidence: 54% of US workers got a job through a connection, yet 21% have never asked for a referral, and only 1 in 10 contact several people a week while job hunting (Networking Nation survey, May 2025). In June 2026, 52% of Indian professionals said they were actively job hunting (foundit).

## 3. Vision and scope

**Vision:** one assistant for every goal that depends on relationships: job, clients, sales, investors, hires, vendors, community.

**v1 scope:** Career Sprint for Indian tech professionals switching jobs, on Android-first mobile web (installable PWA) plus an official WhatsApp number.

### 3.1 Goal-pack roadmap (context for engine design, NOT v1 scope)

| Phase | Pack | First customers | Pricing |
|---|---|---|---|
| 1 (v1) | Career Sprint | Job switchers | ₹799 once, 60 days |
| 1 (v1) | Stay in Touch (free) | Everyone | Free |
| 2 | Freelance & Clients | Freelancers, agencies | Pro ₹299/mo |
| 2 | Event Follow-up | Event attendees, organisers | Pro or organiser-paid |
| 3 | Sales & Partnerships | Sales/BD teams | Teams ₹999/seat/mo |
| 3 | Fundraising | Founders | Pack or Premium |
| 3 | Hiring | Founders, managers | Pack or Teams |
| 3 | Outsourcing & Vendors | Small business owners | Pro |
| 4 | Community & Alumni | Colleges, accelerators | Licence |

**Engine requirement:** adding a pack must need only a new `packs` row (config) plus copy and prompt templates — no new tables, services or forks.

## 4. Users

### 4.1 Primary persona (v1): The Switcher

Rohan, 26, software engineer at a Pune IT services company, 3 years in, wants a product-company role. 800 LinkedIn connections; 40 batchmates already at product companies.

- **Job to be done:** "Get me 5 referrals in 30 days without feeling like I'm begging."
- **Triggers:** disappointing appraisal, a friend's switch, layoff rumours.
- **Today:** scrolls LinkedIn, sends generic "can you refer me?" to 3 people, gives up.
- **Fear:** looking desperate to people he hasn't spoken to in two years.
- **Pays:** ₹500–1,000 once, if it clearly ends in interviews.

### 4.2 Secondary (supported by v1, targeted from Phase 2)

- **Solo Builder** (freelancer/agency): keep past clients warm for repeat work.
- **Everyone (free):** birthdays, festivals, catching up.

### 4.3 Explicitly not a v1 user

**The mass cold-outreach hacker** who wants to message hundreds of strangers. Volume caps exist to keep them out.

## 5. Goals, non-goals, success metrics

### 5.1 Goals (v1)

1. A new user gets their **first useful draft within 5 minutes** of signup.
2. A Sprint user gets **at least one referral or interview within 30 days** (target 40% of Sprint users).
3. **3% of signups buy a Sprint** (India app median download-to-paid is 1.4%).
4. **Gross margin ≥ 80%** per paying user; free users cost **< ₹4/month** each.

### 5.2 Non-goals (v1)

- Native iOS/Android apps.
- Phone calls of any kind (AI calling contacts is never allowed).
- Reading the user's inbox, WhatsApp chats or LinkedIn messages.
- Automating LinkedIn or personal WhatsApp (no scraping, no logging in, no sending on behalf).
- Team plans, other goal packs, desktop-optimised layout (must work, needn't be polished).
- Introductions to strangers (Boardy's territory).

### 5.3 Metrics

| Stage | Metric | Target |
|---|---|---|
| North star | Warm replies received per active user per week | Track from beta; no target yet |
| Activate | Import contacts + send 3 messages within 48 h of signup | 40% |
| Pay | Signups who buy a Sprint | 3% |
| Outcome | Sprint users with ≥1 referral/interview in 30 days | 40% |
| Retain | Free users active next month | 45% |
| Expand | Finished Sprints that move to Pro | 15% |
| Quality | Drafts sent with ≤ 20% edits | 60% (proposed) |

## 6. Product principles (non-negotiable)

These override any feature request. The coding agent must enforce them in code review.

1. **The user sends, never the app.** Messages go out from the user's own WhatsApp/LinkedIn via open-chat links or copy. No login to LinkedIn/personal WhatsApp, no scraping, no sending on behalf.
2. **Nothing leaves without a tap.** Every outbound message to a contact is a draft until the user sends it themselves.
3. **No mass messaging.** Max 20 send actions per user per day (configurable). No bulk-send UI.
4. **Free must cost almost nothing.** Free tier: weekly digest via push/email, small-model drafts, no WhatsApp messages initiated by us, no frontier models.
5. **Goal packs are configuration, not forks.**
6. **Store the minimum.** Delete raw audio after transcription. One-tap export and delete. No selling/sharing contact data. No ads.
7. **Defensible providers.** Contact data only to providers we've approved (see tech spec). No DeepSeek first-party API.
8. **The bot only talks to the user.** Our WhatsApp number never messages a user's contacts.
9. **Honest drafts.** A draft never states a fact that isn't in the user's memories/contact data. Warm-up messages never contain an ask.

## 7. Functional requirements

Priority: **P0** = required for private beta; **P1** = required for public launch; **P2** = nice to have.
IDs are referenced by the sprint plan and tests.

### 7.1 Accounts and onboarding

| ID | Requirement | Pri |
|---|---|---|
| FR-AUTH-1 | Sign up / sign in with Google or email one-time code (Supabase Auth). | P0 |
| FR-AUTH-2 | Sign out; session persists on the installed PWA. | P0 |
| FR-AUTH-3 | User profile: display name, language (English/Hinglish/Hindi/Marathi), timezone (default Asia/Kolkata), nudge time (default 09:00). | P0 |
| FR-ONB-1 | Onboarding is 3 steps: set goal → import people → (optional) writing style; user can skip steps 2–3 and resume later. | P0 |
| FR-ONB-2 | After onboarding the user lands on Today with a ranked list already built (synchronous first ranking run). | P0 |
| FR-ONB-3 | Itemised privacy notice + consents shown at signup (see 7.11). | P0 |

### 7.2 Goals and packs

| ID | Requirement | Pri |
|---|---|---|
| FR-GOAL-1 | Pack picker shows Career Sprint (active) and other packs as "Coming soon" (disabled), driven by `packs` table config. | P0 |
| FR-GOAL-2 | Career Sprint goal fields: target role (text), target companies (list, 1–15), locations (list), referrals target (1–10, default 4), optional job links (used in ask drafts), deadline (default start + 60 days). | P0 |
| FR-GOAL-3 | One active goal per user in v1 (data model supports many). | P0 |
| FR-GOAL-4 | Edit goal; pause/end goal. | P1 |

### 7.3 Contacts (people)

| ID | Requirement | Pri |
|---|---|---|
| FR-CON-1 | Import phone contacts via Contact Picker API on Android Chrome (name, phone, email; multi-select). | P0 |
| FR-CON-2 | Import `.vcf` vCard file (fallback for iPhone/desktop). | P0 |
| FR-CON-3 | Import LinkedIn `Connections.csv` (handles the notes preamble; maps first/last name, URL, email, company, position, connected-on). In-app step-by-step export help; "remind me later" because LinkedIn emails the archive later. | P0 |
| FR-CON-4 | Add a person manually (name required; phone, email, LinkedIn URL, company, title, how you know them optional). | P0 |
| FR-CON-5 | Dedupe on import by normalised phone (E.164, default region IN), lower-cased email, normalised LinkedIn URL; show a preview "X new, Y merged, Z skipped" before committing. | P0 |
| FR-CON-6 | Fuzzy name match suggestions for possible duplicates (never auto-merge on name alone). | P1 |
| FR-CON-7 | Import of 1,000 contacts completes in < 30 s and shows progress; partial failures keep successful rows and list skipped rows with reasons. | P0 |
| FR-CON-8 | People list with search by name/company; Person page (see 7.6). | P0 |
| FR-CON-9 | Edit/delete a person; deleting removes memories, interactions, suggestions, drafts for them. | P0 |

### 7.4 Memories and capture

| ID | Requirement | Pri |
|---|---|---|
| FR-MEM-1 | Add a text note to a person (stored as a memory). | P0 |
| FR-MEM-2 | Voice capture in app: record (MediaRecorder), live timer, stop; upload; transcribe; extract people + facts + commitments + follow-up date; show confirm cards. | P0 |
| FR-MEM-3 | Confirm card per extracted person: Save as new / Merge with suggested existing / Edit / Discard. Nothing is saved without confirmation. | P0 |
| FR-MEM-4 | Confirmed follow-up date creates a dated suggestion for that day. | P0 |
| FR-MEM-5 | Raw audio deleted after transcription; deletion logged. | P0 |
| FR-MEM-6 | Text quick-capture box with the same extraction ("met Priya at eChai…"). | P0 |

### 7.5 Today (daily ranked list)

| ID | Requirement | Pri |
|---|---|---|
| FR-TODAY-1 | Nightly ranking per active goal produces 3–7 suggestions per user for the next day (default 5); max 2 per company per day. | P0 |
| FR-TODAY-2 | Each card shows name, role/company, 1–3 reason chips, stage badge (Warm up / Ask / Thank / Follow up), and actions: Open draft, Snooze (1 day / 1 week), Not relevant. | P0 |
| FR-TODAY-3 | Goal strip at top: day N of 60, days left, counts (warmed up, asked, replied, referrals / target). | P0 |
| FR-TODAY-4 | Free-tier users see the list in a weekly digest (Monday) instead of daily; Today screen still shows the current week's list. | P0 |
| FR-TODAY-5 | Empty states: no contacts → import cards; no goal → goal setup; all done → "You're done for today" + capture prompt. | P0 |
| FR-TODAY-6 | Stay-in-Touch triggers (birthdays, Diwali/New Year, met-recently) appear even without a goal. | P1 |

### 7.6 Person page

| ID | Requirement | Pri |
|---|---|---|
| FR-PER-1 | Header: initials avatar, name, title · company · city, how you know them. | P0 |
| FR-PER-2 | Actions: Draft message, Add note, Voice memory. | P0 |
| FR-PER-3 | Next step card (stage + goal). | P0 |
| FR-PER-4 | "What you remember" list with source and date. | P0 |
| FR-PER-5 | History timeline from `interactions`. | P0 |

### 7.7 Drafts and sending

| ID | Requirement | Pri |
|---|---|---|
| FR-DRAFT-1 | Generate a draft for (person, goal, stage) using memories, contact data, goal params, style profile, language, tone. 2–4 short lines (≤ 90 words). | P0 |
| FR-DRAFT-2 | Tone chips: Shorter, Warmer, More formal, Hinglish; "Another version". | P0 |
| FR-DRAFT-3 | "Why this person, why now" explanation (from ranking reasons). | P0 |
| FR-DRAFT-4 | Fact check: every factual claim must be supported by memories/contact data; unsupported → regenerate once → else show with a warning and highlight. | P0 |
| FR-DRAFT-5 | Warm-up stage drafts contain no ask; ask stage includes a specific, easy ask (e.g., referral for a named role, offer to send resume). | P0 |
| FR-DRAFT-6 | User can edit the draft text inline; final text stored for evaluation. | P0 |
| FR-SEND-1 | "Send on WhatsApp" opens `https://wa.me/<E.164 digits>?text=<urlencoded>`; disabled with explanation if no phone. | P0 |
| FR-SEND-2 | "Copy for LinkedIn" copies text and opens the person's LinkedIn URL (if any). | P0 |
| FR-SEND-3 | On returning to the app, ask "Sent?" (Yes / Not yet); "Mark as sent" button as fallback. | P0 |
| FR-SEND-4 | A send creates `interactions(type='sent')`, marks the suggestion done, schedules a reply check-in in 3 days. | P0 |
| FR-SEND-5 | Daily send cap (default 20); the 21st send action is blocked with a friendly message. | P0 |

### 7.8 Reply tracking and progress

| ID | Requirement | Pri |
|---|---|---|
| FR-REP-1 | "Did they reply?" lists people messaged 2–5 days ago with Replied / Not yet / Referred me (or Snooze for non-goal messages). | P0 |
| FR-REP-2 | Logging "Referred me" or "Interview" updates goal progress and creates a Thank stage suggestion with a thank-you draft. | P0 |
| FR-REP-3 | Badge count of pending reply check-ins in bottom nav. | P0 |
| FR-PROG-1 | Progress screen: warm replies this week (north star), days left, pipeline funnel (warmed up → asked → replied → referred → interview), by-company list. | P0 |

### 7.9 WhatsApp assistant (our official number)

| ID | Requirement | Pri |
|---|---|---|
| FR-WA-1 | Link WhatsApp: button opens `wa.me/<our number>?text=START <link code>`; inbound message verifies phone ↔ account and records opt-in. | P0 |
| FR-WA-2 | Inbound text note → extraction → confirm card reply with Save / Edit in app buttons. | P0 |
| FR-WA-3 | Inbound voice note (Ogg/Opus) → same pipeline as in-app voice. | P0 |
| FR-WA-4 | Daily brief (utility template) at the user's nudge time for paying users only: up to 3 names + reason, buttons "Show drafts" / "Snooze today". | P0 |
| FR-WA-5 | "Show drafts" (inside 24-h window) sends each draft as a separate message so the user can forward/copy. | P0 |
| FR-WA-6 | Commands: TODAY, HELP, STOP (opt-out, immediate), START (opt back in). | P0 |
| FR-WA-7 | Bot never messages anyone except the account's verified phone. | P0 |

### 7.10 Monetisation

| ID | Requirement | Pri |
|---|---|---|
| FR-PAY-1 | Plans: Free; Career Sprint ₹799 one-time for 60 days; Pro ₹299/month or ₹2,499/year. Prices include GST. Prices configurable server-side. | P0 (Sprint), P1 (Pro) |
| FR-PAY-2 | Free limits: 3 AI drafts per calendar month; weekly digest; no WhatsApp brief; small-model drafts only. | P0 |
| FR-PAY-3 | Paywall appears when free draft limit is hit or user tries a paid-only action; shows plan cards per design. | P0 |
| FR-PAY-4 | Web checkout via Razorpay (UPI first, cards); entitlement activated only by verified webhook. | P0 |
| FR-PAY-5 | Sprint fair-use cap: 400 drafts per Sprint (protects margins); configurable. | P0 |
| FR-PAY-6 | Day 50 of a Sprint: in-app + WhatsApp offer of Pro. | P1 |
| FR-PAY-7 | Price A/B test support (₹499 / ₹799 / ₹999) by cohort flag. | P1 |

### 7.11 Privacy and data rights

| ID | Requirement | Pri |
|---|---|---|
| FR-PRIV-1 | Separate, itemised consents: contact import, voice processing, WhatsApp messages, analytics. Withdrawable in Settings. | P0 |
| FR-PRIV-2 | Export all my data (JSON + CSV zip) from Settings. | P0 |
| FR-PRIV-3 | Delete account and all data from Settings with a typed confirmation; completes within 24 h; logged. | P0 |
| FR-PRIV-4 | Privacy policy and terms pages (placeholder legal text marked for lawyer review). | P0 |

### 7.12 Notifications

| ID | Requirement | Pri |
|---|---|---|
| FR-NOT-1 | Web push (installed PWA) for daily nudge (paid) / weekly digest (free). | P1 |
| FR-NOT-2 | Weekly email digest for free users with opt-out link. | P1 |

### 7.13 Analytics and admin

| ID | Requirement | Pri |
|---|---|---|
| FR-AN-1 | Event tracking per tech spec §13 (server-side event table). | P0 |
| FR-AN-2 | Admin metrics page (owner only): funnel, activation, conversion, north star, AI cost per user. | P1 |

## 8. Screens (v1)

Visual reference: Design canvas "Networking Assistant App Screens" and `design/` folder. Details in `04-DESIGN-GUIDE.md`.

1. Sign in · 2. Set your goal · 3. Bring in your people · 4. Writing style (optional) · 5. Today · 6. Draft sheet · 7. Person · 8. People list · 9. Capture (voice/text) · 10. Did they reply? · 11. Progress · 12. Upgrade · 13. Settings & privacy · plus WhatsApp conversation flows.

## 9. Assumptions to validate (from research)

| Assumption | Value used | How we'll learn |
|---|---|---|
| Signup → Sprint purchase | 3% | Beta funnel |
| Best Sprint price | ₹799 | Concierge + A/B |
| Sprint → Pro | 15% | Day-50 offer |
| Drafts per Sprint user per month | 60 | Usage logs |
| Drafts needing frontier model | 25% | Blind test Groq vs Claude |
| Free users active month to month | 45% | Cohorts |

## 10. Open questions

1. Legal basis/notice for storing third parties' (contacts') data under DPDP — lawyer review before public launch.
2. Google Contacts import via People API — check OAuth verification requirements before building (P2).
3. Groq vs Claude draft quality — blind test with 20 users before Sprint 3 ends.
4. Sarvam vs Whisper on Hinglish voice notes — test before Sprint 5.
5. Final app name and brand.

## 11. Release criteria

**Private beta (200–300 users):** all P0 done; activation flow < 5 min on a mid-range Android phone; no P0/P1 bugs open; privacy review done; cost per Sprint user ≤ ₹60/month AI+WhatsApp.

**Public launch (target 1 Apr 2027):** all P1 done; 40% activation and ≥ 3% paid in beta; lawyer sign-off on privacy notices.
