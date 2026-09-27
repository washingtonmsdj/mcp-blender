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

After creating the Cloudflare resources and setting the Worker secret
`ORDAX_OPERATOR_TOKEN`, call the operator-only `POST /v3/devices` endpoint once.
The raw device token is returned once; write it to:

`%LOCALAPPDATA%\\OrdaX\\DevAgent\\device-token.txt`

Then set:

```json
{
  "control_plane_protocol": "cloudflare-v3",
  "control_plane_url": "https://<worker-host>",
  "development_device_id": "<uuid>"
}
```

No Supabase key is required by v3.

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
