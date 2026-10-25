# ADR-0009: Native Windows development against a cloud Supabase dev project

- Status: Accepted (25 Oct 2026). Changes the local setup in tech spec §4 and the Sprint 0 Makefile.

## Context
The founder develops on Windows and doesn't want to maintain WSL2 or a local Supabase stack (about ten containers). A Supabase cloud project already exists for development. CI runs on Linux.

## Decision
- Development runs natively on Windows (PowerShell). Dev commands are root `package.json` scripts (`pnpm dev`, `pnpm check`, `pnpm test`, …) that work in Windows and Linux shells. The Makefile is removed.
- Local development uses a **cloud Supabase dev project** (no real users), in `ap-south-1` like every environment. Staging and production are separate projects created later.
- Rules for the dev project: never reset it or run destructive SQL; schema changes only via new migrations applied with `pnpm db:push` after the human agrees; integration tests run inside transactions that roll back.
- Connect through the **Session pooler** (port 5432): the direct host is IPv6-only and the transaction pooler breaks asyncpg prepared statements. The API accepts the plain `postgresql://` URL.
- The Data API is switched off in the dev project's dashboard (ADR-0007).
- CI keeps a throwaway Supabase CLI stack on Linux runners, so CI never needs project secrets and never touches the dev project.
- Redis still runs locally (Docker Desktop) or as a managed instance via `REDIS_URL`.

## Consequences
- No offline development and no free resets; test data must clean up after itself.
- Developers share one dev database; acceptable for a solo founder.
- Supersedes `docs/DEV-SETUP-WSL.md` (replaced by `docs/DEV-SETUP.md`).
