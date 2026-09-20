-- Keep OrdaX Dev Agent presence truthful when a workstation disappears.
-- Heartbeats and running-job lease renewals arrive roughly every 20 seconds.
-- After 90 seconds without presence, the persisted status becomes offline.

create extension if not exists pg_cron;

create or replace function public.ordax_dev_agents_touch_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke all on function public.ordax_dev_agents_touch_updated_at()
  from public, anon, authenticated;
grant execute on function public.ordax_dev_agents_touch_updated_at()
  to service_role;

drop trigger if exists ordax_dev_agents_touch_updated_at
  on public.ordax_dev_agents;

create trigger ordax_dev_agents_touch_updated_at
before update on public.ordax_dev_agents
for each row execute function public.ordax_dev_agents_touch_updated_at();

create or replace function public.ordax_expire_stale_dev_agents(
  p_stale_after interval default interval '90 seconds'
)
returns integer
language plpgsql
set search_path = public
as $$
declare
  v_expired integer;
begin
  if p_stale_after is null
     or p_stale_after < interval '30 seconds'
     or p_stale_after > interval '1 hour' then
    raise exception 'p_stale_after must be between 30 seconds and 1 hour';
  end if;

  update public.ordax_dev_agents
  set status = 'offline'
  where status <> 'offline'
    and (
      disabled_at is not null
      or last_seen_at is null
      or last_seen_at < now() - p_stale_after
    );

  get diagnostics v_expired = row_count;
  return v_expired;
end;
$$;

revoke all on function public.ordax_expire_stale_dev_agents(interval)
  from public, anon, authenticated;
grant execute on function public.ordax_expire_stale_dev_agents(interval)
  to service_role;

do $$
declare
  v_job_id bigint;
begin
  select jobid
    into v_job_id
  from cron.job
  where jobname = 'ordax-dev-agent-presence-expiry'
  limit 1;

  if v_job_id is not null then
    perform cron.unschedule(v_job_id);
  end if;

  perform cron.schedule(
    'ordax-dev-agent-presence-expiry',
    '* * * * *',
    $cron$
      select public.ordax_expire_stale_dev_agents(interval '90 seconds');
    $cron$
  );
end;
$$;

do $$
begin
  perform public.ordax_expire_stale_dev_agents(interval '90 seconds');
end;
$$;
