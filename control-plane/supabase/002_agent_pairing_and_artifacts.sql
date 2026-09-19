-- Pairing, leased jobs and private artifact storage for OrdaX Dev Agent.

alter table public.ordax_dev_agents
  add column if not exists machine_id_hash text unique,
  add column if not exists token_hash text unique,
  add column if not exists agent_version text,
  add column if not exists paired_at timestamptz,
  add column if not exists disabled_at timestamptz,
  add column if not exists last_job_id uuid,
  add column if not exists last_error text;

create table if not exists public.ordax_dev_pairing_tokens (
  id uuid primary key default gen_random_uuid(),
  code_hash text not null unique,
  agent_name_hint text,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.ordax_dev_pairing_tokens enable row level security;
revoke all on public.ordax_dev_pairing_tokens from anon, authenticated;
grant all on public.ordax_dev_pairing_tokens to service_role;

create policy ordax_dev_pairing_tokens_deny_client_access
  on public.ordax_dev_pairing_tokens
  for all to anon, authenticated
  using (false) with check (false);

alter table public.ordax_dev_jobs
  add column if not exists lease_token uuid,
  add column if not exists leased_until timestamptz,
  add column if not exists attempts integer not null default 0;

create or replace function public.ordax_claim_dev_job(p_agent_name text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_job public.ordax_dev_jobs%rowtype;
  v_lease uuid := gen_random_uuid();
begin
  select *
    into v_job
  from public.ordax_dev_jobs
  where agent_name = p_agent_name
    and (
      status = 'queued'
      or (
        status = 'running'
        and leased_until is not null
        and leased_until < now()
      )
    )
  order by created_at asc
  for update skip locked
  limit 1;

  if not found then
    return null;
  end if;

  update public.ordax_dev_jobs
  set status = 'running',
      started_at = coalesce(started_at, now()),
      lease_token = v_lease,
      leased_until = now() + interval '5 minutes',
      attempts = attempts + 1
  where id = v_job.id;

  return jsonb_build_object(
    'id', v_job.id,
    'agent_name', v_job.agent_name,
    'project_slug', v_job.project_slug,
    'action', v_job.action,
    'payload', v_job.payload,
    'lease_token', v_lease
  );
end;
$$;

revoke all on function public.ordax_claim_dev_job(text) from public, anon, authenticated;
grant execute on function public.ordax_claim_dev_job(text) to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'ordax-dev-artifacts',
  'ordax-dev-artifacts',
  false,
  52428800,
  array[
    'image/png',
    'image/jpeg',
    'application/json',
    'text/plain',
    'application/zip'
  ]
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
