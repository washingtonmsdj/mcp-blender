# OrdaX Dev Agent

OrdaX Dev Agent is the local control plane companion for Unity, Blender, Git, diagnostics and visual feedback.

## Goal

Replace ad-hoc CMD/PowerShell recovery with a persistent, auditable agent that can:

- synchronize approved repository branches safely;
- compile, validate and run Unity;
- execute approved Blender automation;
- collect logs and compiler errors;
- capture gameplay screenshots and structured snapshots;
- publish heartbeats, jobs, events and artifact metadata to Supabase;
- accept only whitelisted actions;
- preserve local work before any Git operation;
- run unattended after Windows sign-in.

The agent does **not** expose arbitrary remote shell execution.

## Architecture

```text
ChatGPT / GitHub / Codex
          |
          | jobs + observations
          v
Supabase control plane
  agents / jobs / events / artifacts
          |
          | authenticated polling/realtime
          v
OrdaX Dev Agent (Windows)
          |
          +---- Git safe sync
          +---- Unity CLI / Editor automation
          +---- Blender CLI / Python
          +---- diagnostics / logs
          +---- screenshot + telemetry
          |
          v
HORDAX / future OrdaX projects
```

## Safety model

The cloud sends a typed action such as `unity.validate` or `git.sync`.
The local agent maps that action to a known Python function. There is no
`shell.exec` action in the default registry.

Potentially destructive operations require an explicit action implementation
with preflight checks and a backup/rollback strategy.

Secrets stay local in environment variables or Windows Credential Manager.
Never commit service keys.

## Initial action registry

- `agent.status`
- `git.status`
- `git.sync`
- `unity.compile`
- `unity.validate`
- `unity.capture`
- `unity.run_method`
- `blender.version`
- `blender.run_python`

Later:

- `blender.render_preview`
- `artifact.upload`
- `artifact.sign`
- `unity.playtest_suite`
- `git.create_diagnostic_branch`

## Supabase

For the temporary integration, use the active Supabase project **Ordax-2026-1**.
The control-plane tables are isolated with the `ordax_dev_` prefix so they do
not overlap the existing application's tables. This is temporary: later we can
migrate the control plane to a dedicated Supabase project without changing the
local agent protocol.

Suggested tables:

- `ordax_dev_agents`: registered machines/capabilities/heartbeat
- `ordax_dev_projects`: allowed local projects per agent
- `ordax_dev_jobs`: typed commands and state
- `ordax_dev_job_events`: append-only logs/progress
- `ordax_dev_artifacts`: screenshots, JSON snapshots, logs and hashes

Use RLS for client-visible tables. The agent should authenticate as a dedicated
machine identity. Realtime can then wake the agent as new jobs arrive, with
polling retained as a fallback.

## Visual loop

For Unity/HORDAX:

1. sync branch;
2. compile;
3. run project validation;
4. capture Game View;
5. write gameplay JSON snapshot;
6. upload the image + snapshot;
7. record the artifact in Supabase;
8. ChatGPT inspects both image and structured state;
9. create the next Git change.

This is the target closed loop that removes repeated manual screenshots and
PowerShell commands.


## Background Unity playtests

The agent can keep HORDAX running even when Unity is not the foreground
application.

- `unity.play_start` enters Play Mode through the in-Editor companion.
- `unity.play_stop` exits Play Mode through the companion.
- `unity.capture` can capture the already-running Game View without stopping it.
- development runtime sets `Application.runInBackground = true`.
- normal background play control does not require the user to click the Unity
  window or Game tab.

For source-code iterations, the preferred chain is:

`play_stop -> git.sync -> refresh -> validate -> play_start`

This gives the user a persistent development preview while still allowing safe
script recompilation between iterations.


## Visible Blender live workspace

The agent can keep a normal Blender window open on the user's desktop while
automation changes the scene. This is intentionally different from the existing
background render/inspection path.

Actions:

- `blender.live_start`: opens one managed interactive Blender session for the project.
- `blender.live_status`: reads heartbeat and scene telemetry without changing the scene.
- `blender.live_inspect`: returns bounded structured object/collection data from the open scene.
- `blender.live_result`: retrieves the durable result of a prior command by ID, including
  after a timeout or after Blender closes. Query this before retrying a timed-out mutation.
- `blender.live_run_script`: executes only a Python file inside the project's approved
  Blender automation directory, in the already-open Blender process.
- `blender.live_capture`: captures the currently visible 3D viewport and publishes it
  through the normal artifact pipeline.
- `blender.live_save`: saves only to a `.blend` path inside the registered project.
- `blender.live_stop`: closes only the managed visible Blender session.

The Blender companion uses a project-scoped file inbox/response protocol under
the OrdaX Dev Agent state directory. It does not expose a generic remote Python
console or arbitrary shell execution. The user can watch mesh, material, camera
and scene changes appear in the Blender viewport as the approved scripts run.

This gives the development loop two visible modes:

`Unity Editor open -> live gameplay changes`

`Blender open -> live asset / scene changes`

Background CLI observation remains available when a visible window is not needed.


### Blender Live timeout safety

Every live command now writes an immutable-by-convention result record under the local
agent state before publishing the transient response. If the caller times out after
Blender has already accepted a command, the timeout includes `command_id`. Call
`blender.live_result` with that ID before deciding whether to retry. The companion keeps
the 200 most recent small JSON results per project; scene files and assets are not copied
or uploaded by this mechanism.


## Long-running Blender Live operations

Blender physics, render, bake and other heavy operations can block Blender's main UI thread. The Live bridge must not interpret that expected silence as a crashed session.

The companion now writes a per-command file under `blender-live/<project>/inflight/` immediately before executing a command and removes it only after the durable result/response has been written. While that marker exists:

- stale presence heartbeat means **busy**, not dead;
- the caller still obeys the requested total timeout;
- a timed-out command must be queried with `blender.live_result` before any retry;
- a missing durable result reports whether the command is still `in_progress`;
- restarting a fresh companion clears abandoned inflight markers.

`blender.live_inspect` also returns filtered `ordax_*` custom properties for scene objects and the scene itself. Generated asset pipelines should use these fields for stable component/role identification and validation reports instead of relying only on display names.
