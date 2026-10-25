# ADR-0007: Supabase Data API off; server-managed columns not writable by users

- Status: Accepted (25 Oct 2026)

## Context
Supabase exposes the `public` schema through its Data API (PostgREST/GraphQL) to anyone holding the anon key, which ships to the browser for auth. With the draft's `for all` owner policies, a signed-in user could call the Data API directly and:
- set their own `profiles.wa_phone_e164` to someone else's number (breaks "the bot only messages the user's verified number"),
- change `price_cohort` or `utm`,
- insert `interactions` or edit `goal_contacts`, `suggestions`, `drafts` and so dodge the send cap or forge progress.

ADR-0002 already says the frontend uses Supabase only for auth and all data goes through our API.

## Decision
- Turn off the Data API: `supabase/config.toml` `[api] enabled = false` (and `schemas = []`) locally; on every hosted project (staging, production) switch the Data API off in the dashboard (or, if the toggle is unavailable, remove `public` and `graphql_public` from **Exposed schemas**). Part of the environment setup checklist.
- `revoke all` on every `public` table, sequence and function from `anon`. Default privileges for future objects revoke `anon` too.
- Column-level privileges on `profiles`: `authenticated` may `update` only user-editable columns (`display_name`, `language`, `timezone`, `nudge_time`, `onboarding_step`). `wa_phone_e164`, `wa_opt_in_at`, `wa_opt_out_at`, `wa_last_inbound_at`, `price_cohort`, `utm` are written only by the service role.
- RLS stays on every table as the second layer: the API still runs user requests as `authenticated` under RLS (tech spec §5.1).
- Automated tests: RLS enabled on every table; `anon` has no table privileges; `authenticated` cannot update server-managed profile columns.

## Consequences
- The browser can't read or write data with the Supabase client; everything goes through `/v1`. This is the intended design.
- New server-managed columns on user-editable tables must be left out of the column grant (review rule).
