# ADR-0001: Mobile-first PWA, not a native app, for v1

- Status: Accepted (25 Oct 2026)

## Context
Target users are Indian tech professionals on Android phones. We need contact import, voice recording, opening WhatsApp with a prefilled message, push notifications and payments. One founder plus a coding agent must ship by April 2027.

## Decision
Build an installable PWA with Next.js, tuned for Android Chrome. WhatsApp is the second surface.

- Contact Picker API works in Android Chrome 80+ (user-selected contacts, multi-select, name/email/tel). iPhone and desktop fall back to vCard upload.
- Web Share Target works for installed PWAs on Android Chrome 76+ (P2 feature).
- `wa.me/<number>?text=` opens WhatsApp with a draft on every platform.
- Web checkout via Razorpay costs ~2.4% vs 11–15% via Google Play billing for digital goods.

## Consequences
- No full address-book access; users pick contacts. Acceptable for v1.
- Go native (Trusted Web Activity first, React Native only if needed) when: users ask for full address-book import, beta shows iPhone users blocked, or background capture is required.

Sources: web.dev Contact Picker API; Chrome Developers Web Share Target; Report 4 payment fees.
