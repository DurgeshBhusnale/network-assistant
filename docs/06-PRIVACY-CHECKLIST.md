# Privacy, Security and Compliance Checklist

India's Digital Personal Data Protection (DPDP) Rules were notified on 13–14 Nov 2025 with a phased rollout: consent-manager provisions from Nov 2026 and the main consent, notice, breach and data-principal-rights obligations from **May 2027** (one month after our planned public launch). We build to those obligations from day one. **This checklist is engineering guidance, not legal advice; a lawyer must review before public launch.**

## Data we hold

| Data | Whose | Why | Retention |
|---|---|---|---|
| Account (email, name, timezone) | User | Run the account | Until account deletion |
| WhatsApp number | User | Link the assistant | Until unlink/deletion |
| Contacts (names, phones, emails, company, title, LinkedIn URL, birthday) | **Third parties**, provided by the user | Core feature | Until the user deletes them or the account; soft-deleted contacts purged after 30 days |
| Memories, notes, transcripts | User about third parties | Drafting, recall | Until deleted; transcripts kept as memories only after the user confirms |
| Raw audio | User | Transcription only | **Deleted immediately after transcription** |
| Drafts (generated + final text) | User | Show history, evaluate quality | 180 days, then delete text (keep metadata) |
| WhatsApp message metadata | User | Delivery status, cost | 90 days; no bodies ever stored |
| Payments | User | Billing, tax | As required by tax law (verify period with CA) |
| Analytics events, AI call logs | User | Product metrics, cost | 13 months |

## Engineering checklist

- [ ] Itemised notice at signup: what data, why, which processors (Supabase, Groq, Anthropic, Sarvam, Meta WhatsApp, Razorpay, Resend, Sentry), where (India for the database), rights, grievance contact.
- [ ] Separate consents (contacts, voice, WhatsApp, analytics), versioned, withdrawable; features check consent at call time.
- [ ] Data minimisation in AI prompts: no phones/emails; only fields needed.
- [ ] Database and storage in Supabase `ap-south-1`; backups enabled.
- [ ] RLS on every table + automated test that fails if a table lacks RLS.
- [ ] Service-role key only on the server; never shipped to the browser.
- [ ] TLS everywhere; HSTS; CSP that allows only our domains + Razorpay checkout + Supabase.
- [ ] Webhook signature verification (WhatsApp, Razorpay), constant-time compare.
- [ ] Log redaction filter (phones, emails, message text, transcripts) + test.
- [ ] Sentry: scrub request bodies and PII; `send_default_pii=False`.
- [ ] Audio deletion after transcription, with `audit_log` row; hourly sweep deletes any leftover audio older than 1 hour.
- [ ] Export my data (zip) and delete my account (≤ 24 h), both logged.
- [ ] Rate limits on send, draft, import, link-code endpoints.
- [ ] Dependency audit in CI (`pnpm audit`, `pip-audit`); secrets scanning.
- [ ] Admin access limited to `ADMIN_USER_IDS`; admin views show aggregates, not contact data.

## Breach runbook (summary)

1. Contain: rotate keys, disable affected endpoints, preserve logs.
2. Assess within 24 h: what data, whose, how many.
3. Notify the Data Protection Board and affected users as required, within 72 hours of becoming aware.
4. Post-mortem and fixes; record in `docs/incidents/`.

## Open legal questions (for the lawyer)

1. Basis and notice for processing third parties' (contacts') data supplied by our user.
2. Whether we're a Significant Data Fiduciary at any scale we'd reach (unlikely in v1).
3. Retention period for payment records; GST invoicing requirements.
4. Terms of use for WhatsApp Business messaging and opt-in wording.
