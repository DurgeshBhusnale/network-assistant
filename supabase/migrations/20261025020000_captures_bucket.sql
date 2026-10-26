-- Sprint 5: private bucket for voice captures. Audio is deleted right after transcription
-- (FR-MEM-5); an hourly sweep removes anything older than an hour. Only the service role
-- (API/worker) touches it: uploads use short-lived signed URLs, so no storage.objects policies.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'captures',
  'captures',
  false,
  16777216,
  array['audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/aac']
)
on conflict (id) do nothing;
