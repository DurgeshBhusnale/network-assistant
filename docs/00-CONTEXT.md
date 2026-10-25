# Context — why this product exists

A one-page summary of the founding research (5 reports in the claude.ai project "Networking Assistant"). Read this to understand the *why* behind decisions in the PRD and tech spec.

## The problem (Report 1)

People meet valuable contacts, intend to follow up, and don't. The four failure points are capture, recall, trigger and act; existing tools fix capture and trigger (reminders) but not recall and act. Evidence: 54% of US workers got a job through a connection, but 21% have never asked for a referral (Networking Nation, May 2025). Users of personal CRMs consistently complain about manual data entry. **Implication:** the product must do the work (rank, remember, draft), not add reminders.

## The market (Report 2)

- Personal CRMs: Dex ($12–20/mo), Mesh (ex-Clay, acquired by Automattic 2025, $10/mo), Covve, Monica. All "remind you"; none goal-driven, none India/WhatsApp-native.
- AI connectors: Boardy ($8M seed, Creandum, Jan 2025) introduces strangers via voice/WhatsApp. Happenstance (YC W24) searches your network.
- India: 200.7M LinkedIn users (Sep 2026), ~half aged 25–34.
- **White space:** goal-driven, works your existing network, India/WhatsApp-native, rupee pricing.

## The customer (Report 3)

- First customer: Indian tech professionals switching jobs ("The Switcher"). 52% of Indian professionals said they were actively job hunting in June 2026 (foundit).
- Second: freelancers/agencies (stay and pay monthly). Later: founders, connectors, sales teams.
- Do not build for mass cold-outreach users.

## The business model (Report 4)

- Free core; **Career Sprint ₹799 once for 60 days**; Pro ₹299/mo or ₹2,499/yr; later Premium ₹2,999/mo, Teams ₹999/seat, partner licences.
- Per-user gross margin 77–91% only if: most drafts on small models (Groq gpt-oss), WhatsApp only for paying users, free users on push/email. A free user must cost < ₹4/month.
- Paid ads don't pay back in India (₹48 median cost per signup; 1.4% India download-to-paid). Growth must be organic.
- Provider comparison: Groq-only stack ≈ ₹9 AI cost per Sprint user/month; Claude stack ≈ ₹23. Choose by draft quality; route only high-stakes drafts to frontier models.

## Go-to-market (Report 5)

Pune-first, founder-led, ad-free. Concierge Sprints by hand → MVP → private beta (200–300) → public launch April 2027 (appraisal season). North-star metric: **warm replies received per user per week**.

## What this means for the code

- Optimise for **time to first useful draft** (< 5 min) and **drafts sent with few edits**.
- Every cost-bearing action (AI, WhatsApp) must be gated by plan and logged.
- The engine must stay pack-agnostic so later goals ship as configuration.
