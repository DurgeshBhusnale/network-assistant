# Design Guide — Networking Assistant (v4)

**Source:** the v4 design canvas ("Networking Assistant v4", 26 Oct 2026). Reference markup: `design/screens/Networking Assistant v4.dc.html` and `design/screens/BottomNavV4.dc.html` (with `support.js`). They use a canvas runtime (`<x-dc>`), so they won't run standalone: open them as text and copy layout, spacing and colours. Tokens: `design/tokens.css`. The older v1 files in `design/screens/` are superseded.

> Quiet, spacious, precise. 24 px gutters, an 8 px rhythm, hairline borders instead of heavy shadows, and one gradient reserved for the primary action.

## Principles

1. **Phone first.** Design at 390 × 844 (Android mid-range). Desktop centres a 480 px column.
2. **Today is a short list, never a database.** Max 7 cards; each card answers who, why now, what next.
3. **One primary action per screen**, and only it gets the accent gradient. Everything else is secondary (hairline), tonal (soft accent) or ghost.
4. **Calm, not gamified.** No streaks, confetti or guilt copy. Progress is factual.
5. **Trust is visible.** "Nothing is sent until you tap send" under send actions; a lock + privacy line on import and capture.

## Foundations

| Token | Value | Use |
|---|---|---|
| Canvas | `--color-canvas-top` #FFFFFF → `--color-bg` #F4F5FD | Page background (vertical fade) |
| Surface | `--color-surface` #FFF | Cards, nav, sheets, bottom bars |
| Surface 2 | `--color-surface-2` #F4F5FD | Panels inside screens ("Why her, why now"), tags |
| Field | `--color-field` #F1F2FA | Search field |
| Ink | `--color-ink` #14183A | Text, dark button ("Yes, merge"), selected chip |
| Ink 2 / Muted | #4A5075 / `--color-muted` #5F658A | Secondary text / meta, captions, section labels |
| Hairline | `--color-line` #E6E8F4 | Card outlines, dividers |
| Hairline strong | `--color-line-strong` #D5D9EE | Inputs, secondary buttons, chips |
| Accent text | `--color-primary` #3D3FC0 | Links, active nav, section labels in accent, "Ask" badge |
| Accent soft | `--color-primary-soft` #EEF0FF | Tonal buttons, active nav pill, avatars on Today header |
| Accent gradient | `--color-grad-from` #3B5BDB → `--color-grad-to` #6D4AE8 | Primary buttons, capture FAB, progress fills, checks, bullet dots |
| Indigo ink | `--color-hero-from` #141B4D → `--color-hero-to` #32258A | Today hero card, voice capture panel |
| Tint | #E4E9FF → #EBE0FF | Next-step card, "Sent?" prompt, check-before-sending |
| Info | #E3F3FF → #E4E9FF, text #0B5E8A | Referral card, done states, "Thank" badge |
| Badge neutral | #F1F2F9 / #4A5075 | "Warm up", "Follow up", company status |
| Avatars | `--avatar-1…6` (oklch 0.93/0.04 fill, 0.36/0.1 text) | Initials avatar, hue picked by a stable hash of the name |
| Danger | #B4321F | Destructive actions only |

Utilities in `apps/web/app/globals.css`: `bg-grad`, `bg-grad-bar`, `bg-hero`, `bg-tint`, `bg-info`, `text-grad`, `hairline`, `hairline-strong`, `ring-selected`, `label-caps`, `title` (28 px), `title-lg` (32 px). Element defaults live in `@layer base` so utilities always win.

**Type:** **Bricolage Grotesque** 600 for titles and big numbers (display 56–64 "1 of 4", title 28–32, letter-spacing −0.02 to −0.04em); **Figtree** 400–700 for everything else. Heading 18/600; body 15–17 with 22–28 line height; secondary 14/20; labels 12/700 caps +0.08em. Loaded with `next/font/google`.

**Space and shape:** 24 px screen gutters; 8 px rhythm with 8 / 16 / 28 gaps (28 between sections). Card padding 20–24. Radii: cards 24, hero and draft card 28, goal tiles 20, buttons 16 (48 px) / 18 (56 px CTA), badges 12, chips pill. Hairlines (inset box-shadow) instead of borders; soft lifts only on cards (`shadow-card`), the hero (`shadow-hero`) and the primary CTA (`shadow-cta`).

**Icons:** inline stroke SVG, 1.8 px stroke, 18–24 px (`components/ui/icons.tsx`). No emoji in UI.

## Components

| Component | Spec |
|---|---|
| `Button` | primary (gradient, white text; 56 px `lg` with CTA shadow, 48 px `md`), secondary (white + strong hairline), tonal (accent soft), dark (ink), ghost (accent text), danger. `buttonClasses()` gives links the same look. |
| `IconButton` | 44 px round, strong hairline, `aria-label` required. |
| `Card` | White, radius 24, padding 20, hairline + soft lift. |
| `PersonCard` (Today) | Avatar 48, name 17/600, role · company 14 muted, StageBadge right; reason tags (13 px, surface-2, highlight in accent soft); "Open draft" primary + 48 px snooze button. |
| `GoalStrip` (hero) | Indigo gradient, radius 28, padding 24: caps label + "Day N of M"; display count + "of 4 referrals"; 4 px progress (soft gradient); 3 stats split by hairlines. |
| `StageBadge` | 24 px, radius 12, 12/600: Ask (accent soft), Warm up / Follow up (neutral), Thank (info). |
| `Chip` | Reason tags (13 px, radius 14). Tone chips on Draft: 44 px pills, selected = ink. |
| `BottomNav` | 92 px incl. safe area; tab = 56×30 pill (accent soft when active) + 11 px label; centre 58 px gradient mic FAB raised 26 px with a white ring; Replies count badge in ink. Shown only on the four tab screens; detail screens use a back button. |
| `BottomBar` | Pinned action bar on detail screens: "solid" (white 95% + top hairline: Draft, Upgrade) or "fade" (canvas fade: onboarding). |
| `Stepper` | Label left, "− 4 +" pill right (48 px). |
| `ChipInput` | Accent-soft chips with remove, "+ Add" pill with accent hairline. |
| `ProgressSteps` | 3 bars (4 px, gradient when done) + "Step N of 3". |
| `ConfirmCard` | Avatar + name, "Role · New contact" or "Is this X? / Possible duplicate"; facts with gradient dots; follow-up in a surface-2 chip; Save + Edit, or Yes, merge (dark) + New person. |
| `SectionLabel` | 12/700 caps, muted or accent. |
| `EmptyState` | Centred: 104 px tinted icon disc, 24 px display title, one line, primary action + optional text link. |
| `Sheet` | Bottom sheet for notes, snooze and stage choice; tiles are 64 px hairline rows. |

## Screens

| Screen | Key content | Primary action |
|---|---|---|
| Today | Date line, "Good evening, {name}" (title 28), initial avatar → Settings; indigo hero; "Today's people · N · about M min"; PersonCards; empty: "Nobody to contact yet" + Add your contacts / Or speak who you met | Open draft |
| Draft | Back + avatar 44 + name/role; caps stage label in accent; draft card (17/28 text, "N words · in your voice", Edit); tone chips (scroll); "Try another version"; "Why {name}, why now" panel; bottom bar: Send on WhatsApp, Copy for LinkedIn + Mark as sent, trust line | Send on WhatsApp |
| Person | Back + more; avatar 96 with ring; name (title 28); role · company · city; "how you know them" pill; three round actions (Draft message gradient, Add note, Voice memory); Next step (tint); What you remember rows; History timeline | Draft message |
| People | "People" (title 32) + "N contacts" + round add; search field; A–Z groups (accent letters), 68 px rows with 44 px avatars; no-results: "No one found for “X”" + Add someone by hand (tonal). Filter chips: later. | — |
| Did they reply? | Title 32 + reassurance line; referral card (info) with Draft a thank-you; per person: Replied / Not yet / Referred me (tonal) | Per-card buttons |
| Progress | Caps "Career Sprint · Day N"; gradient display "1 of 4" + "referrals"; 6 px bar; two stat cards; pipeline bars (lightest → gradient); By company rows with status badge | — |
| Onboarding · Goal | Step 1/3; 2×2 tiles (selected: tint fill, accent ring, gradient check); role, company chips, referrals stepper, location; Continue in fade bar | Continue |
| Onboarding · People | Step 2/3; phone contacts (info card when added), LinkedIn steps with numbered dots + Upload CSV (tonal) / Remind me later; add by hand row; lock + privacy line | Continue with N people (secondary "Skip for now" while empty) |
| Voice capture | Indigo panel to the edge, radius 40 at the bottom: caps "Listening", prompt (24 display), gradient waveform, timer, white stop/record button; "Found N people" + ConfirmCards | Save |
| Upgrade | Close; title 32; reason line; gradient-bordered Career Sprint card (badge, ₹799, Pay once · 60 days, 4 checks); Pro card only when `PRO_ENABLED`; bottom bar: Pay ₹799 with UPI, Pay by card, "Prices include GST" | Pay with UPI |
| Sign in, Consents, Writing style, Settings, Admin, Legal, Offline | Not in the canvas: built from the same components (title 28–32, cards, hairline fields, gradient primary). | — |

## Copy rules

- Plain, warm, specific. Use the person's first name.
- Buttons say exactly what happens: "Send on WhatsApp", "Copy for LinkedIn", "Mark as sent", "Pay ₹799 with UPI".
- Never guilt ("You haven't messaged anyone in 5 days!"). Prefer "3 people for today".
- Errors say what went wrong and what to do: "Couldn't read that file. Upload the Connections.csv from LinkedIn's export."
- Prices always include "GST included" nearby.

## Accessibility

Contrast ≥ 4.5:1 (tokens comply: muted #5F658A on the canvas ≈ 5.2:1; white on both gradient ends ≥ 4.9:1); touch targets ≥ 44 px; real form labels; logical focus order; `aria-live` for draft generation and capture processing status; respects reduced motion; TalkBack tested.
