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
The first delivery left the running Agent unchanged during another remote
session. The user subsequently authorized restart; deployment is recorded below.

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

## Deployment observed on 2026-09-25

Published code commit `b978585` and ran the noninteractive managed setup with a
180-second readiness deadline. It completed with `ORDAX_DEVICE_AGENT=READY`.
Local status then reported Agent 1.20.5, `state=ready`, PID 11616, supervisor
12872, 166 actions and a heartbeat age of 15.3 seconds at observation.
`startup_seconds=2.277` measures Agent main entry to its first accepted heartbeat.
This was a service restart on an already running Windows system, not a cold OS
boot benchmark; it must not be compared directly with the earlier reboot timing.
No test suite or Blender modeling job was run during this deployment.

## 1.20.6: terminal delivery reliability

Inspection of the deployed `ordax_report_develop_job_v2` confirmed a 65,536-byte
JSON result limit and replay support for an identical report id and payload.
V2 artifact previews now cap binary data at 32 KiB, leaving room for base64 and
metadata. Oversized previews return the existing size error; request smaller
thumbnail dimensions in that case.

Terminal reports retry transport failures and HTTP 408/429/500/502/503/504 up to
three total attempts, with one- and two-second delays. Every attempt reuses the
same report id and content. Authorization failures and permanent rejections are
not retried. This is bounded in-process recovery, not a durable outbox across
process restarts or an indefinite network outage.

Lease renewal now remains active until report delivery finishes. A failed optional
progress event no longer prevents sending the terminal result. No Blender action
is repeated by this retry loop. No fault-injection or test suite was run for this
change; deployment readiness is a separate operational observation.
