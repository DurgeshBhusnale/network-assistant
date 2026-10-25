# ADR-0004: The user sends; the app never messages contacts

- Status: Accepted (25 Oct 2026)

## Context
Automating LinkedIn or personal WhatsApp breaks their terms and gets accounts banned. Messages that come from a bot damage the relationships we are trying to strengthen. Our WhatsApp Business number is billed per message and governed by Meta's policies.

## Decision
- Outbound messages to a user's contacts are only ever sent by the user from their own device: `wa.me` deep links with prefilled text, or copy + open LinkedIn profile.
- Our WhatsApp number only talks to the account owner's verified number (enforced by a guard in the WhatsApp client).
- Sent/replied status is user-reported (one tap), since we never read the user's chats.
- Daily send-action cap (default 20) and no bulk-send UI.

## Consequences
- Tracking relies on user taps; UX must make logging effortless ("Sent?" on return, reply check-ins).
- We give up "fully automatic outreach" by design; this is a trust feature in positioning.
