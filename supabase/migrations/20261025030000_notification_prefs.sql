-- Sprint 7: weekly email digest preference (FR-NOT-2). User-editable (ADR-0007 column grants).
alter table profiles add column email_digest boolean not null default true;
grant update (email_digest) on profiles to authenticated;
