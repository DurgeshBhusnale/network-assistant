# Developer setup (Windows)

Development runs natively on Windows against the cloud Supabase **dev** project (ADR-0009). Commands below are PowerShell.

## 1. Tools (one time)

| Tool | Check | Install if missing |
|---|---|---|
| Git | `git --version` | `winget install Git.Git` |
| Node.js 24 LTS | `node -v` | `winget install OpenJS.NodeJS.LTS` |
| pnpm | `pnpm -v` | `corepack enable` (version pinned in `package.json`) |
| uv (installs Python 3.12 itself) | `uv --version` | `winget install astral-sh.uv` |
| Supabase CLI (migrations only) | `supabase --version` | `scoop install supabase` |
| Redis | see §3 | Docker Desktop (needs WSL2: `wsl -l -v` must answer), or a managed Redis |

## 2. Configure `.env`

Copy `.env.example` to `.env` (git-ignored) and fill in, from the Supabase dashboard of the dev project:

- `SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`: `https://<project-ref>.supabase.co`
- `SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`: **Settings → API Keys**
- `DATABASE_URL`: **Connect → Session pooler** (port 5432). Not the direct connection (IPv6-only) and not the transaction pooler (6543).
- `GROQ_API_KEY`: console.groq.com. Keep `AI_MODE=fake` unless you are demoing live drafts.

Dashboard checklist: Data API **off** (ADR-0007). Region: the current dev project is Seoul (accepted for dev only, ADR-0009); staging/production must be **ap-south-1 (Mumbai)**.

## 3. Redis

Either:
- **Docker Desktop** (needs WSL2 or Hyper-V enabled in Windows features): `pnpm bootstrap` runs `docker compose up -d redis`; `REDIS_URL=redis://localhost:6379/0`.
- **Managed Redis** (e.g. Upstash, Mumbai region): set `REDIS_URL=rediss://default:<password>@<host>:6379`. No Docker needed.

## 4. Run

```powershell
pnpm bootstrap      # deps + Redis container
pnpm db:push        # first time only, and after new migrations (ask before running on shared DBs)
pnpm dev            # web http://localhost:3000, API http://localhost:8000/v1/health, worker
```

Before saying a change is done: `pnpm check; pnpm test` (and `pnpm test:int` for API/DB/worker changes).

## 5. Testing on an Android phone

PWA install and service workers need HTTPS or `localhost`, so a LAN IP won't do. Use USB port forwarding:

1. Phone: Developer options → USB debugging on; connect by USB.
2. Desktop Chrome → `chrome://inspect/#devices` → **Port forwarding** → `3000` → `localhost:3000` → enable.
3. Phone Chrome → `http://localhost:3000`. The web app proxies `/api/*` to the API, so only port 3000 is needed.

For install/offline checks use a production build: `pnpm --filter web build; pnpm --filter web start`.
