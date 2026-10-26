-- Networking Assistant — schema DRAFT (v1), kept in sync with the first migration.
-- The applied schema is supabase/migrations/20261025000000_init_schema.sql; later changes
-- go in new migrations only. Seed data: supabase/seed.sql (generated from packs/*.json).
--
-- Source: docs/schema-draft.sql, with ADR-0007 (no Data API, server-managed columns)
-- and ADR-0008 (stages/outcomes as text validated against pack config).
-- Assumes Supabase (auth.users, auth.uid(), roles anon/authenticated/service_role).

create extension if not exists vector with schema extensions;
create extension if not exists pg_trgm with schema extensions;

-- ---------------------------------------------------------------------------
-- Enums (generic only; pack vocabulary is text, see ADR-0008)
-- ---------------------------------------------------------------------------
create type pack_status as enum ('active', 'coming_soon', 'retired');
create type goal_status as enum ('active', 'paused', 'done');
create type suggestion_status as enum ('pending', 'opened', 'sent', 'snoozed', 'dismissed', 'expired');
create type memory_source as enum ('note', 'voice', 'whatsapp', 'import');
create type import_source as enum ('picker', 'vcard', 'linkedin_csv', 'manual');
create type capture_source as enum ('app_audio', 'app_text', 'wa_audio', 'wa_text');
create type job_status as enum ('queued', 'processing', 'ready', 'committed', 'failed');
create type product_code as enum ('sprint', 'pro_monthly', 'pro_yearly');
create type consent_type as enum ('contacts', 'voice', 'whatsapp', 'analytics');

-- ---------------------------------------------------------------------------
-- Helper: updated_at trigger
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at() returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Profiles
-- ---------------------------------------------------------------------------
create table profiles (
  user_id            uuid primary key references auth.users (id) on delete cascade,
  display_name       text,
  language           text not null default 'en' check (language in ('en', 'hinglish', 'hi', 'mr')),
  timezone           text not null default 'Asia/Kolkata',
  nudge_time         time not null default '09:00',
  onboarding_step    text not null default 'goal' check (onboarding_step in ('goal', 'import', 'style', 'done')),
  -- Server-managed (ADR-0007): not writable by the authenticated role.
  wa_phone_e164      text unique,
  wa_opt_in_at       timestamptz,
  wa_opt_out_at      timestamptz,
  wa_last_inbound_at timestamptz,
  price_cohort       text,
  utm                jsonb not null default '{}'::jsonb,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
create trigger profiles_updated_at before update on profiles for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Packs (config) and goals
-- ---------------------------------------------------------------------------
create table packs (
  id         text primary key,
  name       text not null,
  status     pack_status not null default 'coming_soon',
  sort_order int not null default 100,
  config     jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table goals (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  pack_id    text not null references packs (id),
  params     jsonb not null default '{}'::jsonb,
  status     goal_status not null default 'active',
  starts_on  date not null,   -- user's local date, set by the API (no UTC default)
  ends_on    date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index goals_user_idx on goals (user_id);
create unique index goals_one_active_per_user on goals (user_id) where status = 'active';
create trigger goals_updated_at before update on goals for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Contacts and memories
-- ---------------------------------------------------------------------------
create table contacts (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users (id) on delete cascade,
  full_name           text not null,
  first_name          text,
  last_name           text,
  phones              text[] not null default '{}',   -- E.164
  emails              text[] not null default '{}',   -- lower-cased
  linkedin_url        text,                           -- normalised https://www.linkedin.com/in/<slug>
  company             text,
  company_norm        text,
  title               text,
  city                text,
  how_known           text,
  birthday            date,
  sources             import_source[] not null default '{}',
  last_interaction_at timestamptz,
  deleted_at          timestamptz,                    -- soft delete; row purged after 30 days
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index contacts_user_idx on contacts (user_id) where deleted_at is null;
create index contacts_phones_idx on contacts using gin (phones);
create index contacts_emails_idx on contacts using gin (emails);
create index contacts_linkedin_idx on contacts (user_id, linkedin_url);
create index contacts_name_trgm_idx on contacts using gin (full_name extensions.gin_trgm_ops);
create index contacts_company_idx on contacts (user_id, company_norm);
create trigger contacts_updated_at before update on contacts for each row execute function public.set_updated_at();

create table memories (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  contact_id uuid not null references contacts (id) on delete cascade,
  text       text not null check (char_length(text) <= 2000),
  source     memory_source not null,
  embedding  extensions.vector(384),   -- unused until an ADR picks the embedding provider
  created_at timestamptz not null default now()
);
create index memories_contact_idx on memories (contact_id, created_at desc);
create index memories_user_idx on memories (user_id);

-- ---------------------------------------------------------------------------
-- Goal ↔ contact state, suggestions, drafts, interactions
-- ---------------------------------------------------------------------------
create table goal_contacts (
  goal_id           uuid not null references goals (id) on delete cascade,
  contact_id        uuid not null references contacts (id) on delete cascade,
  user_id           uuid not null references auth.users (id) on delete cascade,
  relevance_label   text,
  relevance         real,
  relevance_reason  text,
  state             text not null default 'none' check (state in ('none', 'warmed', 'asked', 'replied', 'won')),
  outcome           text,          -- one of the pack's outcomes (validated in app)
  last_suggested_at timestamptz,
  last_sent_at      timestamptz,
  thanked_at        timestamptz,
  dismissed_at      timestamptz,
  updated_at        timestamptz not null default now(),
  primary key (goal_id, contact_id),
  check ((state = 'won') = (outcome is not null))
);
create index goal_contacts_user_idx on goal_contacts (user_id);
create index goal_contacts_contact_idx on goal_contacts (contact_id);
create trigger goal_contacts_updated_at before update on goal_contacts for each row execute function public.set_updated_at();

create table suggestions (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  goal_id       uuid references goals (id) on delete cascade,
  contact_id    uuid not null references contacts (id) on delete cascade,
  for_date      date not null,
  score         real not null,
  reasons       jsonb not null default '[]'::jsonb,
  stage         text not null,   -- pack stage id (validated in app)
  status        suggestion_status not null default 'pending',
  snoozed_until date,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index suggestions_user_date_idx on suggestions (user_id, for_date);
create index suggestions_contact_idx on suggestions (contact_id);
create unique index suggestions_unique_per_day on suggestions (user_id, contact_id, for_date);
create trigger suggestions_updated_at before update on suggestions for each row execute function public.set_updated_at();

create table drafts (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users (id) on delete cascade,
  suggestion_id  uuid references suggestions (id) on delete set null,
  contact_id     uuid not null references contacts (id) on delete cascade,
  stage          text not null,   -- pack stage id (validated in app)
  tone           text,
  language       text not null default 'en',
  provider       text not null,
  model          text not null,
  prompt_version text not null,
  text           text not null,
  final_text     text,
  regenerations  int not null default 0,   -- tone changes / "Another version" on this draft
  factcheck      jsonb not null default '{}'::jsonb,
  sent_channel   text check (sent_channel in ('whatsapp', 'linkedin', 'other')),
  send_opened_at timestamptz,             -- first POST /drafts/{id}/send; counts toward the daily cap
  sent_at        timestamptz,
  created_at     timestamptz not null default now()
);
create index drafts_user_idx on drafts (user_id, created_at desc);
create index drafts_user_send_idx on drafts (user_id, send_opened_at) where send_opened_at is not null;
create index drafts_contact_idx on drafts (contact_id);

create table interactions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  contact_id  uuid not null references contacts (id) on delete cascade,
  goal_id     uuid references goals (id) on delete set null,
  type        text not null check (type in ('met', 'sent', 'replied', 'no_reply', 'note', 'outcome')),
  stage       text,   -- pack stage id for 'sent' (validated in app)
  outcome     text,   -- pack outcome for 'outcome' (validated in app)
  channel     text,
  occurred_at timestamptz not null default now(),
  meta        jsonb not null default '{}'::jsonb,
  check ((type = 'outcome') = (outcome is not null))
);
create index interactions_contact_idx on interactions (contact_id, occurred_at desc);
create index interactions_user_type_idx on interactions (user_id, type, occurred_at desc);

create table style_profiles (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  samples    text[] not null default '{}',
  summary    text,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Triggers (timing signals) and calendar
-- ---------------------------------------------------------------------------
create table calendar_events (
  id     uuid primary key default gen_random_uuid(),
  date   date not null,
  name   text not null,
  kind   text not null default 'festival',
  active boolean not null default true,
  unique (date, name)
);

create table triggers (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  contact_id uuid not null references contacts (id) on delete cascade,
  type       text not null check (type in ('birthday', 'festival', 'met_recently', 'job_change')),
  date       date not null,
  created_at timestamptz not null default now()
);
create index triggers_user_date_idx on triggers (user_id, date);
create unique index triggers_unique on triggers (contact_id, type, date);

-- ---------------------------------------------------------------------------
-- Imports and captures
-- ---------------------------------------------------------------------------
create table imports (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  source     import_source not null,
  status     job_status not null default 'queued',
  counts     jsonb not null default '{}'::jsonb,   -- {new, merged, skipped}
  errors     jsonb not null default '[]'::jsonb,   -- [{row, reason}]
  preview    jsonb,                                -- staged rows until commit; cleared after commit
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index imports_user_idx on imports (user_id, created_at desc);
create trigger imports_updated_at before update on imports for each row execute function public.set_updated_at();

create table captures (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users (id) on delete cascade,
  source           capture_source not null,
  storage_path     text,
  wa_media_id      text,
  language         text,
  transcript       text,   -- cleared on confirm/discard; unconfirmed swept after 24 h
  extracted        jsonb,
  status           job_status not null default 'queued',
  error            text,
  audio_deleted_at timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index captures_user_idx on captures (user_id, created_at desc);
create trigger captures_updated_at before update on captures for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- WhatsApp
-- ---------------------------------------------------------------------------
create table wa_link_codes (
  code       text primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  expires_at timestamptz not null,
  used_at    timestamptz
);
create index wa_link_codes_user_idx on wa_link_codes (user_id);

create table wa_messages (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users (id) on delete cascade,
  direction     text not null check (direction in ('in', 'out')),
  kind          text not null,
  template_name text,
  wa_message_id text unique,
  status        text,
  created_at    timestamptz not null default now()
  -- No message bodies are stored by design.
);
create index wa_messages_user_idx on wa_messages (user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Billing
-- ---------------------------------------------------------------------------
create table payments (
  id                  uuid primary key default gen_random_uuid(),
  -- Kept (anonymised) after account deletion for tax records.
  user_id             uuid references auth.users (id) on delete set null,
  provider            text not null default 'razorpay',
  product             product_code not null,
  amount_paise        int not null check (amount_paise > 0),
  currency            text not null default 'INR',
  status              text not null default 'created' check (status in ('created', 'paid', 'failed', 'refunded')),
  provider_order_id   text unique,
  provider_payment_id text unique,
  raw_event_id        text unique,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index payments_user_idx on payments (user_id);
create trigger payments_updated_at before update on payments for each row execute function public.set_updated_at();

create table entitlements (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users (id) on delete cascade,
  product           product_code not null,
  starts_at         timestamptz not null default now(),
  ends_at           timestamptz not null,
  drafts_used       int not null default 0,
  source_payment_id uuid references payments (id) on delete set null,
  created_at        timestamptz not null default now()
);
create index entitlements_user_idx on entitlements (user_id, ends_at desc);

-- ---------------------------------------------------------------------------
-- Privacy, analytics, AI cost, push, audit
-- ---------------------------------------------------------------------------
create table consents (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  type         consent_type not null,
  version      text not null,
  granted_at   timestamptz not null default now(),
  withdrawn_at timestamptz
);
create index consents_user_idx on consents (user_id, type);

create table events (
  id          bigint generated always as identity primary key,
  user_id     uuid references auth.users (id) on delete cascade,
  name        text not null,
  props       jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now()
);
create index events_name_time_idx on events (name, occurred_at desc);
create index events_user_idx on events (user_id);

create table ai_calls (
  id             bigint generated always as identity primary key,
  user_id        uuid references auth.users (id) on delete cascade,
  task           text not null,
  provider       text not null,
  model          text not null,
  prompt_version text,
  tokens_in      int,
  tokens_out     int,
  audio_seconds  real,
  cost_inr       numeric(10, 4),   -- estimate, not money moved; fractional paise allowed
  latency_ms     int,
  ok             boolean not null,
  created_at     timestamptz not null default now()
);
create index ai_calls_user_time_idx on ai_calls (user_id, created_at desc);

create table push_subscriptions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  endpoint   text not null unique,
  keys       jsonb not null,
  created_at timestamptz not null default now()
);
create index push_subscriptions_user_idx on push_subscriptions (user_id);

create table audit_log (
  id         bigint generated always as identity primary key,
  user_ref   text not null,               -- user id, or a hash of it after account deletion
  action     text not null,
  meta       jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
alter table profiles           enable row level security;
alter table packs              enable row level security;
alter table goals              enable row level security;
alter table contacts           enable row level security;
alter table memories           enable row level security;
alter table goal_contacts      enable row level security;
alter table suggestions        enable row level security;
alter table drafts             enable row level security;
alter table interactions       enable row level security;
alter table style_profiles     enable row level security;
alter table calendar_events    enable row level security;
alter table triggers           enable row level security;
alter table imports            enable row level security;
alter table captures           enable row level security;
alter table wa_link_codes      enable row level security;
alter table wa_messages        enable row level security;
alter table payments           enable row level security;
alter table entitlements       enable row level security;
alter table consents           enable row level security;
alter table events             enable row level security;
alter table ai_calls           enable row level security;
alter table push_subscriptions enable row level security;
alter table audit_log          enable row level security;

-- Read-only reference tables
create policy packs_read on packs for select to authenticated using (true);
create policy calendar_read on calendar_events for select to authenticated using (true);

-- Owner full access (user-editable data)
create policy own_profiles on profiles for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_goals on goals for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_contacts on contacts for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_memories on memories for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_goal_contacts on goal_contacts for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_suggestions on suggestions for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_drafts on drafts for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_interactions on interactions for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_style on style_profiles for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_triggers on triggers for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_imports on imports for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_captures on captures for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_consents on consents for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy own_push on push_subscriptions for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- Owner read-only (written only by server/service role)
create policy read_own_payments on payments for select to authenticated using (user_id = (select auth.uid()));
create policy read_own_entitlements on entitlements for select to authenticated using (user_id = (select auth.uid()));
create policy read_own_wa_codes on wa_link_codes for select to authenticated using (user_id = (select auth.uid()));

-- wa_messages, events, ai_calls, audit_log: no policies for authenticated → service role only.

-- ---------------------------------------------------------------------------
-- Privileges (ADR-0007)
-- ---------------------------------------------------------------------------
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
revoke all on all functions in schema public from anon;
alter default privileges for role postgres in schema public revoke all on tables from anon;
alter default privileges for role postgres in schema public revoke all on sequences from anon;
alter default privileges for role postgres in schema public revoke all on functions from anon;

-- profiles: the authenticated role may only insert/update user-editable columns.
revoke insert, update on profiles from authenticated;
grant insert (user_id, display_name, language, timezone, nudge_time, onboarding_step) on profiles to authenticated;
grant update (display_name, language, timezone, nudge_time, onboarding_step) on profiles to authenticated;
