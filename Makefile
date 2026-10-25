# Networking Assistant — developer commands (Linux / WSL2 Ubuntu; see docs/DEV-SETUP-WSL.md).
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

API := apps/api
API_RUN := cd $(API) && AI_MODE=fake uv run

.PHONY: help setup dev check fmt test test-int e2e gen-api db-reset

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install deps (pnpm, uv), start Supabase + Redis, apply migrations + seed
	pnpm install --frozen-lockfile
	cd $(API) && uv sync --frozen
	@test -f .env || { cp .env.example .env; echo "created .env from .env.example"; }
	docker compose up -d redis
	supabase start
	$(MAKE) db-reset

dev: ## Run web :3000, api :8000, worker; ensures Redis (docker) and Supabase are up
	docker compose up -d redis
	supabase status >/dev/null 2>&1 || supabase start
	pnpm exec concurrently --kill-others-on-fail --names web,api,worker --prefix-colors blue,green,yellow \
	  "pnpm --filter web dev" \
	  "cd $(API) && uv run uvicorn --factory app.main:create_app --reload --host 0.0.0.0 --port 8000" \
	  "cd $(API) && uv run arq app.workers.settings.WorkerSettings --watch app"

check: ## Lint + format check + typecheck (web + api)
	cd $(API) && uv run ruff check . && uv run ruff format --check . && uv run mypy
	pnpm --filter web lint
	pnpm --filter web format:check
	pnpm --filter web typecheck

fmt: ## Auto-fix lint and formatting (web + api)
	cd $(API) && uv run ruff check --fix . && uv run ruff format .
	pnpm --filter web format

test: ## Unit tests (web + api)
	$(API_RUN) pytest -m "not integration"
	pnpm --filter web test

test-int: ## API integration tests (needs `supabase start` and Redis)
	eval "$$(supabase status -o env | sed -n 's/^ANON_KEY=/export SUPABASE_ANON_KEY=/p')"; \
	  $(API_RUN) pytest -m integration

e2e: ## Playwright (Pixel 7 emulation) against a production build
	pnpm --filter web e2e

gen-api: ## Regenerate the TS client types from the FastAPI OpenAPI schema
	$(API_RUN) python -m app.openapi_export
	pnpm --filter web gen-api

db-reset: ## Regenerate supabase/seed.sql from packs/*.json, reset local DB, run migrations + seed
	$(API_RUN) python -m app.db_seed
	supabase db reset
