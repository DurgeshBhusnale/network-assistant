-- Sprint 1: record acknowledgement of the itemised privacy notice (FR-ONB-3), separate from
-- the four optional consents. User-editable through the API (ADR-0007 column grants).
alter table profiles
  add column privacy_notice_version text,
  add column privacy_notice_ack_at  timestamptz;

grant update (privacy_notice_version, privacy_notice_ack_at) on profiles to authenticated;
