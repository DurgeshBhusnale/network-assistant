# ADR-0011: One responsive web app, with a desktop layout

- Status: Accepted (26 Oct 2026). Extends ADR-0001 (PWA first); replaces "desktop just centres a 480 px column" in the design guide.

## Context
The founder wants the product usable in desktop Chrome as well as on the phone, and designed a web layout ("Networking Assistant Web", canvas 1440 × 900) alongside the v4 mobile screens.

## Decision
- Same Next.js app, routes and API; layout switches by viewport width only. Below 1024 px (`lg`) everything is the v4 mobile design, unchanged. From 1024 px: a 248 px left sidebar (logo, Voice capture button, Today / People / Progress / Replies, user block) replaces the bottom nav, and screens use the web compositions (two-column grids, People table, split onboarding / capture / upgrade).
- Still mobile-first: components are built for 390 px and gain `lg:` variants; no desktop-only features or routes.
- E2E keeps the Pixel 7 project and adds a small desktop project (1440 × 900) for layout smoke checks.

## Consequences
- Each screen carries both layouts, so changes must be checked at both widths (design guide lists the desktop compositions).
- Device features stay phone-only where browsers lack them (Contact Picker falls back to vCard upload; recording works in desktop Chrome).
