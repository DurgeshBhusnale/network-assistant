# Networking Assistant — project kickoff pack

An AI relationship assistant that turns the people you already know into the outcome you want. v1: **Career Sprint** (job referrals through your own network) on a generic relationship engine, delivered as a mobile-first PWA plus a WhatsApp assistant.

This folder is the starting point of the repository. It contains the product and technical docs, rules for the coding agent, a sprint plan with tests and acceptance criteria, starter config, and design references. **No application code yet**: the coding agent builds it sprint by sprint.

## What's inside

| Path | What |
|---|---|
| `CLAUDE.md` | Rules for the coding agent (read automatically by Claude Code) |
| `PROMPTS.md` | The prompts to paste into the agent, in order |
| `docs/00-CONTEXT.md` | Why this product exists (research summary) |
| `docs/01-PRD.md` | Product requirements with IDs (FR-…), principles, metrics |
| `docs/02-TECH-SPEC.md` | Architecture, stack, data model, API, engine, AI, WhatsApp, billing, privacy, testing |
| `docs/03-SPRINT-PLAN.md` | 9 sprints: scope, tests, acceptance criteria, demos, regression suite |
| `docs/04-DESIGN-GUIDE.md` | Tokens, components, screen specs |
| `docs/05-AI-PROMPTS-AND-EVALS.md` | v1 prompt texts and evaluation method |
| `docs/06-PRIVACY-CHECKLIST.md` | DPDP-oriented privacy and security checklist |
| `docs/schema-draft.sql` | Initial database schema with RLS |
| `docs/adr/` | Architecture decisions (PWA first, stack, AI routing, user-sends rule, auth, packs as config) |
| `docs/PROGRESS.md` | Living status file the agent updates every session |
| `design/` | `tokens.css` + reference markup for 10 screens from the Design canvas |
| `packs/career_sprint.json` | The first goal pack's configuration |
| `.claude/commands/` | Slash commands: `/start-sprint N`, `/review-sprint N`, `/resume` |
| `.env.example`, `.gitignore`, `docker-compose.yml` | Starter config |

## How to start

1. **Install locally:** Git, Node.js LTS + pnpm, Python 3.12 + uv, Docker Desktop (for Supabase local + Redis), Supabase CLI, Claude Code.
2. **Create the repo:** extract this folder, `cd` into it, `git init`, first commit, push to a private GitHub repo.
3. **Open the agent** in the repo root and paste **Prompt 0** from `PROMPTS.md`. Answer its questions, approve its Sprint 0 plan, then continue with the next prompts.
4. After each sprint, run the verification prompt and test on your Android phone before moving on.

## Accounts to set up (and when)

| Account | Needed by | Notes |
|---|---|---|
| GitHub (private repo) | Sprint 0 | CI runs on GitHub Actions |
| Supabase: staging project (Mumbai `ap-south-1`) | Sprint 1 | Local dev uses the Supabase CLI; enable Google provider + email OTP |
| Google Cloud OAuth client | Sprint 1 | For Google sign-in via Supabase |
| Groq API key | Sprint 3 | Default AI provider |
| Anthropic API key | Sprint 3 | Premium drafts + fallback |
| Sarvam API key | Sprint 5 | Indian-language speech-to-text |
| **Meta Business + WhatsApp Cloud API** | **Start in Sprint 4**, needed Sprint 6 | Business verification and template approval take time |
| **Razorpay** | **Start KYC early**, needed Sprint 7 | Test mode works before KYC completes |
| Vercel (web), Fly.io or AWS Mumbai (API + workers), managed Redis | Before beta (Sprint 8) | Pick hosts with a Mumbai region |
| Resend (email), Sentry | Sprint 7–8 | |

## Ground rules (short version of CLAUDE.md)

The user sends, never the app · nothing leaves without a tap · no mass messaging · the bot only talks to the user · free costs almost nothing · goal packs are config · store the minimum · honest drafts · approved AI providers only.

## Related

- Research reports 1–5, the v1 Build Spec doc and the Design canvas live in the founder's claude.ai project "Networking Assistant".
- Validation runs in parallel with the build: concierge Sprints by hand and the Diwali reconnect test (Report 5). Feed what you learn back into the PRD.
