# OrdaX Control Plane v3 — Cloudflare

This directory is the provider-neutral replacement path for the Device Agent's
high-frequency Supabase development transport.

## Runtime split

- **Worker**: device authentication, operator API and artifact HTTP gateway.
- **Durable Object per device**: one persistent WebSocket, serialized job delivery,
  leases, progress and terminal reports.
- **D1**: devices, jobs, events and artifact metadata.
- **R2**: screenshots, snapshots, GLB/FBX/Blend artifacts under the existing
  project-scoped artifact contract.

The local `ActionRegistry` remains the final authority. This backend never adds a
generic shell capability.

## Why v3

`development-v2` keeps a remote wait request open and refreshes presence on a
fixed cadence. v3 keeps one authenticated WebSocket open instead. Idle stations
therefore stop consuming a new Edge Function invocation every wait/heartbeat cycle.

## Provisioning

Normal Windows provisioning uses `ordax_dev_agent.device_setup` (or
`ordax-device-agent-setup.ps1`) with `cloudflare-v3`. The credential is
generated locally and stored at:

`%LOCALAPPDATA%\\OrdaX\\DevAgent\\device-token.cloudflare-v3.txt`

Only its SHA-256 is sent to the Worker. The existing Supabase v2 credential is
kept separately at `device-token.development-v2.txt` during migration.

`agent-settings.json` keeps `control_plane_identities` for each provider and
the active `control_plane_protocol` / `development_device_id`. No Supabase key
is required by v3.

## Deployment order

1. Create D1 database `ordax-control-plane-v3`.
2. Replace the D1 id in `wrangler.toml`.
3. Create R2 bucket `ordax-device-artifacts`.
4. Apply `migrations/0001_initial.sql`.
5. Set `ORDAX_OPERATOR_TOKEN` as a Worker secret.
6. Deploy the Worker.
7. Provision a device and test it before changing the active Windows transport.

Supabase remains active during migration. Remove it only after v3 has passed a
real Device Agent job, artifact upload/download, reconnect and Windows restart.

### Artifact integrity

Artifact uploads are streamed directly to R2 with the agent-provided SHA-256
passed to R2 as a native checksum. R2 rejects a body whose bytes do not match the
declared digest. The Worker also verifies the returned object size and checksum
before writing artifact metadata to D1; a mismatch is deleted and never exposed
through a signed read URL.

### Terminal report replay

Terminal job results carry a unique `report_id` stored in D1. An identical replay
with the same lease, execution epoch, runtime identity, status, result digest,
result JSON and error code is acknowledged as already committed. Any divergent
replay is rejected as `terminal_report_conflict`.

### Durable terminal outbox

The Device Agent persists terminal reports under its local state directory before
network delivery. Startup recovery uses `POST /v3/device/recover-report` with the
device credential and the original execution context, before opening the device
WebSocket. D1 accepts the report only if that execution context is still current,
or acknowledges it if the identical terminal report was already committed.

A `running` job is never re-leased automatically. It fences later jobs for that
device until terminal recovery succeeds or an operator resolves the stalled job.
This prevents an expired lease from becoming an implicit second execution of a
Blender/Unity/Git mutation.
