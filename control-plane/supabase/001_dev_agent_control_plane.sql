-- OrdaX Dev Agent control plane.
-- Apply to a dedicated Supabase project.

create extension if not exists pgcrypto;

create table if not exists public.dev_agents (
  id uuid primary key default gen_random_uuid(),
  agent_name text not null unique,
  status text not null default 'offline'
    check (status in ('offline','online','busy','error')),
  capabilities jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dev_jobs (
  id uuid primary key default gen_random_uuid(),
  agent_name text not null references public.dev_agents(agent_name) on update cascade,
  project_slug text,
  action text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued'
    check (status in ('queued','running','succeeded','failed','cancelled')),
  result jsonb,
  requested_by uuid default auth.uid(),
  idempotency_key text unique,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create index if not exists dev_jobs_agent_status_created_idx
  on public.dev_jobs(agent_name, status, created_at);

create table if not exists public.dev_job_events (
  id bigint generated always as identity primary key,
  job_id uuid not null references public.dev_jobs(id) on delete cascade,
  level text not null default 'info',
  message text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists dev_job_events_job_id_id_idx
  on public.dev_job_events(job_id, id);

create table if not exists public.dev_artifacts (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.dev_jobs(id) on delete cascade,
  agent_name text not null references public.dev_agents(agent_name) on update cascade,
  kind text not null,
  file_name text,
  storage_path text,
  signed_url text,
  sha256 text,
  size_bytes bigint,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.dev_agents enable row level security;
alter table public.dev_jobs enable row level security;
alter table public.dev_job_events enable row level security;
alter table public.dev_artifacts enable row level security;

-- No anon access.
revoke all on public.dev_agents from anon;
revoke all on public.dev_jobs from anon;
revoke all on public.dev_job_events from anon;
revoke all on public.dev_artifacts from anon;

-- Authenticated access should be tightened to a dedicated machine identity.
-- The first production pass should add auth_user_id to dev_agents and bind
-- policies to auth.uid(). Until then, use a dedicated project/key only.

alter publication supabase_realtime add table public.dev_jobs;
alter publication supabase_realtime add table public.dev_job_events;
