# Remote responsiveness improvements

## Changes

- Load the legacy Supabase storage SDK only when constructing the legacy transport.
  Development-v2 no longer imports that dependency through the transport factory.
- After an empty v2 wait lasting at least one second, reconnect after 100 ms.
  Immediate empty responses retain idle backoff to avoid a request flood.
- Send device heartbeat during long jobs alongside lease renewal.
- Expose job phases, execution/upload/report/total duration, completed job count,
  process uptime and time to first accepted heartbeat in local `/status`.
- Include execution and upload durations in remote result `data.agent_timings`.
  Report duration is local only because it is known after the result is accepted.
- Show phases, timings and heartbeat age in the localhost dashboard.

## Delivery and limits

These are additive Agent changes; no backend schema or credentials changed.
No tests or performance benchmarks were run for this change. Actual startup
improvement must be measured; no speedup percentage is claimed.
The running Agent is intentionally not restarted while another remote session
is working. The code takes effect after its normal managed update/restart.

The v2 artifact implementation currently returns local artifact metadata with
`delivery=local-only-v2-artifact-gateway-pending`; it does not transfer file bytes
to remote storage. Therefore the upload phase measures artifact preparation for
v2, not proof of remote file delivery. A secure artifact gateway remains follow-up
work. Timing fields do not imply remote preview availability.

Future priorities: acknowledged artifact delivery, durable result retry without
repeating Blender actions, and profiling the action registry import cost.

## 1.20.5: bounded artifact preparation

Artifact checksums are now streamed instead of reading an entire model into RAM.
`artifact.preview` rejects oversized inline files before reading them and bounds
the actual read even if the file grows. JPEG thumbnails request decoder scaling
before resizing and convert to RGB only after reducing dimensions.

V2 results now put metadata-only artifacts in `data.local_artifacts`, with
`artifact_delivery=local-only`, instead of claiming `uploaded_artifacts`.
Consumers needing image bytes can call the existing project-scoped
`artifact.preview` with `thumbnail=true`, `max_width=480`, `max_height=320`,
and `max_bytes=262144`. Its `base64` field contains the actual preview bytes.
This does not implement a large-file storage gateway.
