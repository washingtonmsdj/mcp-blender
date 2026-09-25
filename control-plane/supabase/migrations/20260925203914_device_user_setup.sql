-- Only the authenticated Edge Function may call this atomic credential transaction.
-- SECURITY INVOKER: no privilege escalation through a public RPC.
create or replace function public.ordax_setup_device_v1(
  p_github_user_id text, p_binding text, p_name text, p_token_sha256 text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  d public.ordax_devices%rowtype;
  c public.ordax_device_credentials%rowtype;
begin
  if p_github_user_id is null or p_github_user_id !~ '^[0-9]{1,20}$'
    or p_binding is null or p_binding !~ '^[0-9a-f]{64}$'
    or p_token_sha256 is null or p_token_sha256 !~ '^[0-9a-f]{64}$'
    or p_name is null or length(p_name) not between 1 and 120 or p_name ~ '[[:cntrl:]]'
  then raise exception 'invalid_setup_request'; end if;
  perform pg_advisory_xact_lock(hashtextextended('ordax-setup:' || p_binding, 0));
  select * into d from public.ordax_devices
    where stable_identity in ('machine:' || p_binding, 'github-oidc:' || p_binding)
    for update;
  if found then
    if d.mode <> 'developer' or d.metadata->>'setup_github_user_id' is distinct from p_github_user_id
    then raise exception 'device_owner_mismatch'; end if;
  else
    insert into public.ordax_devices(device_name, stable_identity, mode, status, capabilities, metadata)
    values (p_name, 'machine:' || p_binding, 'developer', 'offline',
      '{"development_v2":true,"blender":true}'::jsonb,
      jsonb_build_object('setup_github_user_id', p_github_user_id,
        'machine_binding_sha256', p_binding, 'enrollment_source', 'user-authenticated-setup'))
    returning * into d;
  end if;
  select * into c from public.ordax_device_credentials where token_sha256 = p_token_sha256;
  if found then
    -- A revoked token can never be resurrected, even by replaying an old request.
    if c.device_id <> d.device_id or c.revoked_at is not null then raise exception 'token_replay_rejected'; end if;
    return jsonb_build_object('ok', true, 'device_id', d.device_id, 'reused', true);
  end if;
  if (select count(*) from public.ordax_device_credentials where device_id=d.device_id
      and created_at > now() - interval '1 hour') >= 10 then raise exception 'rotation_rate_limited'; end if;
  update public.ordax_device_credentials set revoked_at=now()
    where device_id=d.device_id and revoked_at is null;
  insert into public.ordax_device_credentials(device_id, token_sha256, token_hint, scopes)
    values(d.device_id, p_token_sha256, 'local', array['develop_heartbeat','develop_poll','develop_report']);
  return jsonb_build_object('ok', true, 'device_id', d.device_id, 'reused', false);
end;
$$;
revoke all on function public.ordax_setup_device_v1(text,text,text,text) from public, anon, authenticated;
grant execute on function public.ordax_setup_device_v1(text,text,text,text) to service_role;
