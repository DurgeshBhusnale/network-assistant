# ADR-0005: Sign in with Google or email code; verify phone via WhatsApp linking

- Status: Accepted (25 Oct 2026). Supersedes the build spec's "phone OTP via WhatsApp authentication template" for v1 sign-in.

## Context
SMS OTP needs a paid SMS provider and DLT registration in India. WhatsApp authentication templates cost per message and require the WhatsApp setup that lands in Sprint 6. We want sign-in working in Sprint 1 at zero marginal cost.

## Decision
- Sign-in: Supabase Auth with Google OAuth and email one-time code.
- The user's phone is verified when they link WhatsApp: they send `START <code>` from their phone to our number; the inbound webhook proves ownership of that number.

## Consequences
- Users without Google or email access can't sign in (negligible for the target segment).
- Revisit phone-first sign-in after beta if signup drop-off at the email step is high.
