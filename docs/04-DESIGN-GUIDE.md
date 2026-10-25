# Design Guide — Networking Assistant v1

**Source:** Design canvas "Networking Assistant App Screens" (claude.ai Design). Reference markup for every screen is in `design/screens/*.dc.html`: open them as text and copy layout, spacing and colours. They use a canvas runtime (`support.js`, `<x-dc>`), so **they won't run standalone; rebuild them as React components**. Tokens: `design/tokens.css`.

The visual direction is provisional ("refine later"). Build components on tokens so a rebrand is a token change.

## Principles

1. **Phone first.** Design at 390 × 844 (Android mid-range). Desktop just centres a 480 px column in v1.
2. **Today is a short list, never a database.** Max 7 cards; each card answers who, why now, what next.
3. **One primary action per screen** (blue, full width at the bottom or on the card).
4. **Calm, not gamified.** No streaks, confetti or guilt copy. Progress is factual.
5. **Trust is visible.** State "Nothing is sent until you tap send" near send actions; privacy lines on import and capture.

## Foundations

| Token | Value | Use |
|---|---|---|
| Ground | `--color-bg` #F3F5F7 | App background |
| Surface | `--color-surface` #FFF | Cards, nav, sheets |
| Dark surface | `--color-surface-dark` #14171F | Goal strip, stat card, recorder panel |
| Primary | `--color-primary` #2340C9 | Primary buttons, links, active nav, "Ask" badge text |
| Accent (marigold) | `--color-accent` #F2A33A | Capture FAB, referral highlights, "Referred me" button |
| Accent soft / text | #FDF0DC / #7A4300 | Reason chips, next-step card |
| Success | #1C7A4D on #E3F4EA | "Warm up"/"Follow up" badges, done checks |
| Send | #1F7A4A | "Send on WhatsApp" button only |
| Danger | #B4321F | Count badges, destructive actions |

Typography: display **Bricolage Grotesque** (600/700) for screen titles, names on Person, prices, big numbers; UI **Instrument Sans** (400/500/600) for everything else. Scale in `tokens.css`. Load via `next/font/google`.

Layout: screen side padding 20 px; card padding 14 px; gaps 10 px between cards; 8 px grid. Radius: cards 14, panels 16, buttons 10 (44 px) / 12 (52 px CTA), chips pill, badges 6.

Icons: inline stroke SVG, 2 px stroke, 18–24 px (e.g., Lucide set). No emoji in UI.

## Components

| Component | Spec |
|---|---|
| `Button` | Variants: primary (blue), secondary (white + line border), accent (marigold), send (green), ghost. Heights 44 / 52. Loading and disabled states. |
| `IconButton` | 44 × 44, `aria-label` required. |
| `Card` | Surface, 1 px line border, radius 14, padding 14. |
| `PersonCard` (Today) | Avatar (40 px initials, tinted by hash), name 15/600, meta 13 muted, StageBadge top-right, 1–3 ReasonChips, actions row: primary "Open draft" + snooze IconButton. |
| `StageBadge` | Ask (primary on primary-soft), Warm up / Follow up (success on success-soft), Thank (accent-text on accent-soft). 11.5/600, radius 6. |
| `ReasonChip` | Highlight reason: accent-soft/accent-text; neutral: bg/ink-2. 12 px, pill. |
| `GoalStrip` | Dark panel: label "CAREER SPRINT · DAY 12 OF 60", days-left pill (accent), goal title (display 18), 4 stats grid; referrals stat in accent. |
| `BottomNav` | 5 slots: Today, People, Capture FAB (56 px marigold, raised 24 px), Progress, Replies (with danger count badge). Height 76 + safe area. |
| `Stepper` | − value + in a 46 px field. |
| `ChipInput` | Chips + dashed "+ Add" chip (companies, locations). |
| `ProgressSteps` | 3-segment bar + "Step N of 3". |
| `ConfirmCard` | Capture candidate: name, status label (New contact / Possible match), facts, follow-up date in accent-text, two buttons. |
| `FunnelBar` | Label 92 px, track, value; referred bar in accent. Widths proportional to the first stage. |
| `EmptyState` | Title, one line, one action. |
| `Sheet` | Bottom sheet for notes and tone options. |

## Screens

Each references its design file. Copy text is final for v1 unless marked `[ ]`.

| Screen | File | Key content | Primary action |
|---|---|---|---|
| Today (home) | `Main.dc.html` | Date line, "Good morning, {name}", avatar → Settings, GoalStrip, "Today · N people · about M min", PersonCards, BottomNav | Open draft |
| Draft sheet | `Draft.dc.html` | Back, person name + meta, step badge "Step 2 of 3 · Ask for a referral", editable message card with word count and "Another version", tone chips, "Why {name}, why now" bullets, bottom: Send on WhatsApp, Copy for LinkedIn, Mark as sent, trust line | Send on WhatsApp |
| Person | `Person.dc.html` | Avatar 72, name (display 24), title · company · city, how known; 3 action tiles; next-step card; "What you remember" list with source/date; History timeline with coloured dots | Draft message |
| Did they reply? | `Replies.dc.html` | Title + explanation; per person: Replied / Not yet / Referred me (or Snooze); referred state card with "Draft a thank-you"; "Why we ask" dashed note | Per-card buttons |
| Goal progress | `Progress.dc.html` | "1 of 4 referrals", stats (warm replies this week; days left), pipeline funnel, by-company list | — |
| Set your goal | `Goal.dc.html` | ProgressSteps 1/3, title, 2×2 pack tiles (only "Get referred" enabled), role input, company chips, referrals stepper, where | Continue |
| Bring in your people | `Import.dc.html` | ProgressSteps 2/3, phone contacts card (done state), LinkedIn card with 3-step export help + Upload CSV / Remind me later, add-by-hand card, privacy line | Continue with N people |
| Voice capture | `Capture.dc.html` | Close, dark recorder panel (prompt, waveform, timer, stop button, live transcript), "Found N people · check before saving", ConfirmCards, WhatsApp tip | Save per card |
| Upgrade | `Upgrade.dc.html` | Close, title, reason line, Sprint card (badge "Best for a job switch", ₹799 once, 60 days, 4 benefits), Pro card, Pay ₹799 with UPI, Pay by card, GST line | Pay with UPI |
| WhatsApp assistant | `WhatsApp.dc.html` | Not an app screen: the conversation design for the bot (brief template + buttons, draft messages, voice note, capture confirm) | — |

Screens not yet designed (build from components, same style): Sign in, Consents, Writing style, People list, Settings & privacy, Link WhatsApp card, Export/Delete confirmations, error and empty states.

## Copy rules

- Plain, warm, specific. Use the person's first name.
- Buttons say exactly what happens: "Send on WhatsApp", "Copy for LinkedIn", "Mark as sent", "Pay ₹799 with UPI".
- Never guilt ("You haven't messaged anyone in 5 days!"). Prefer "3 people for today".
- Errors say what went wrong and what to do: "Couldn't read that file. Upload the Connections.csv from LinkedIn's export."
- Prices always include "GST included" nearby.

## Accessibility

Contrast ≥ 4.5:1 (tokens comply); touch targets ≥ 44 px; real form labels; logical focus order; `aria-live` for draft generation and capture processing status; respects reduced motion; TalkBack tested.
