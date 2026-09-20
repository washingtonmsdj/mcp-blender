-- Deterministic chained workflows for OrdaX Dev Agent jobs.

alter table public.ordax_dev_jobs
  add column if not exists depends_on_job_id uuid
    references public.ordax_dev_jobs(id) on delete set null,
  add column if not exists workflow_id uuid;

create index if not exists ordax_dev_jobs_dependency_idx
  on public.ordax_dev_jobs(depends_on_job_id);

create index if not exists ordax_dev_jobs_workflow_idx
  on public.ordax_dev_jobs(workflow_id, created_at, id);

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
  update public.ordax_dev_jobs child
  set status = 'cancelled',
      finished_at = now(),
      result = jsonb_build_object(
        'ok', false,
        'summary', 'cancelled because dependency did not succeed'
      )
  from public.ordax_dev_jobs parent
  where child.agent_name = p_agent_name
    and child.status = 'queued'
    and child.depends_on_job_id = parent.id
    and parent.status in ('failed', 'cancelled');

  select candidate.*
    into v_job
  from public.ordax_dev_jobs candidate
  left join public.ordax_dev_jobs parent
    on parent.id = candidate.depends_on_job_id
  where candidate.agent_name = p_agent_name
    and (
      candidate.status = 'queued'
      or (
        candidate.status = 'running'
        and candidate.leased_until is not null
        and candidate.leased_until < now()
      )
    )
    and (
      candidate.depends_on_job_id is null
      or parent.status = 'succeeded'
    )
  order by candidate.created_at asc, candidate.id asc
  for update of candidate skip locked
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
    'lease_token', v_lease,
    'workflow_id', v_job.workflow_id,
    'depends_on_job_id', v_job.depends_on_job_id
  );
end;
$$;

revoke all on function public.ordax_claim_dev_job(text)
  from public, anon, authenticated;
grant execute on function public.ordax_claim_dev_job(text) to service_role;
