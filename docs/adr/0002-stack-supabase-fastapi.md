# ADR-0002: Supabase (Mumbai) + FastAPI (Python) + Next.js

- Status: Accepted (25 Oct 2026)

## Context
We need Postgres with RLS, auth, file storage, data in India, and a backend that's strong at AI orchestration. The founder is experienced with Python, FastAPI, Redis and LangChain-style tooling.

## Decision
- Supabase for Postgres (+pgvector), Auth, Storage, region `ap-south-1` (Mumbai).
- FastAPI (Python 3.12) for the API and arq workers in one codebase; SQLAlchemy 2 async.
- Next.js for the PWA; frontend uses Supabase only for auth; all data via the API.
- RLS is enforced for user requests by running queries as the `authenticated` role with JWT claims set per transaction; workers use the service role with explicit `user_id` scoping.

## Consequences
- Two languages (TS + Python); mitigated by generated API client from OpenAPI.
- We avoid Supabase client-side data access, which keeps business rules (limits, caps, consents) in one place.
