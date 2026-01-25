-- Core tables for Ordax Studio persistence

-- 1) projects
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  name text not null,
  description text,
  game_type text,
  thumbnail_url text,
  is_public boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_projects_user_id on public.projects(user_id);
create index if not exists idx_projects_updated_at on public.projects(updated_at desc);

alter table public.projects enable row level security;

create policy "projects_select_own_or_public"
on public.projects
for select
using (auth.uid() = user_id or is_public = true);

create policy "projects_insert_own"
on public.projects
for insert
with check (auth.uid() = user_id);

create policy "projects_update_own"
on public.projects
for update
using (auth.uid() = user_id);

create policy "projects_delete_own"
on public.projects
for delete
using (auth.uid() = user_id);

-- 2) project_files
create table if not exists public.project_files (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null,
  name text not null,
  type text not null check (type in ('file','folder')),
  path text not null,
  parent_id uuid,
  content text,
  language text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(project_id, path)
);

create index if not exists idx_project_files_project_id on public.project_files(project_id);
create index if not exists idx_project_files_user_id on public.project_files(user_id);

alter table public.project_files enable row level security;

create policy "project_files_select_own_or_public"
on public.project_files
for select
using (
  auth.uid() = user_id
  or exists (
    select 1 from public.projects p
    where p.id = project_id and p.is_public = true
  )
);

create policy "project_files_insert_own"
on public.project_files
for insert
with check (auth.uid() = user_id);

create policy "project_files_update_own"
on public.project_files
for update
using (auth.uid() = user_id);

create policy "project_files_delete_own"
on public.project_files
for delete
using (auth.uid() = user_id);

-- 3) game_specs (versioned)
create table if not exists public.game_specs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null,
  spec_data jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_game_specs_project_id on public.game_specs(project_id);
create index if not exists idx_game_specs_user_id on public.game_specs(user_id);
create index if not exists idx_game_specs_created_at on public.game_specs(created_at desc);

alter table public.game_specs enable row level security;

create policy "game_specs_select_own_or_public"
on public.game_specs
for select
using (
  auth.uid() = user_id
  or exists (
    select 1 from public.projects p
    where p.id = project_id and p.is_public = true
  )
);

create policy "game_specs_insert_own"
on public.game_specs
for insert
with check (auth.uid() = user_id);

create policy "game_specs_delete_own"
on public.game_specs
for delete
using (auth.uid() = user_id);

-- 4) chat_messages
create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_chat_messages_project_id on public.chat_messages(project_id);
create index if not exists idx_chat_messages_user_id on public.chat_messages(user_id);
create index if not exists idx_chat_messages_created_at on public.chat_messages(created_at asc);

alter table public.chat_messages enable row level security;

create policy "chat_messages_select_own"
on public.chat_messages
for select
using (auth.uid() = user_id);

create policy "chat_messages_insert_own"
on public.chat_messages
for insert
with check (auth.uid() = user_id);

create policy "chat_messages_delete_own"
on public.chat_messages
for delete
using (auth.uid() = user_id);

-- 5) project_assets (metadata)
create table if not exists public.project_assets (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null,
  name text not null,
  type text not null,
  url text not null,
  size_bytes bigint not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_project_assets_project_id on public.project_assets(project_id);
create index if not exists idx_project_assets_user_id on public.project_assets(user_id);

alter table public.project_assets enable row level security;

create policy "project_assets_select_own"
on public.project_assets
for select
using (auth.uid() = user_id);

create policy "project_assets_insert_own"
on public.project_assets
for insert
with check (auth.uid() = user_id);

create policy "project_assets_delete_own"
on public.project_assets
for delete
using (auth.uid() = user_id);

-- updated_at trigger helper
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql set search_path = public;

drop trigger if exists update_projects_updated_at on public.projects;
create trigger update_projects_updated_at
before update on public.projects
for each row execute function public.update_updated_at_column();

drop trigger if exists update_project_files_updated_at on public.project_files;
create trigger update_project_files_updated_at
before update on public.project_files
for each row execute function public.update_updated_at_column();

-- Storage bucket for assets (public read)
insert into storage.buckets (id, name, public)
values ('project-assets', 'project-assets', true)
on conflict (id) do nothing;

-- Storage policies (public read, owner write)
-- NOTE: storage.objects is in storage schema; policies are standard for uploads.
create policy "project_assets_public_read"
on storage.objects
for select
using (bucket_id = 'project-assets');

create policy "project_assets_owner_insert"
on storage.objects
for insert
with check (
  bucket_id = 'project-assets'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "project_assets_owner_update"
on storage.objects
for update
using (
  bucket_id = 'project-assets'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "project_assets_owner_delete"
on storage.objects
for delete
using (
  bucket_id = 'project-assets'
  and auth.uid()::text = (storage.foldername(name))[1]
);
