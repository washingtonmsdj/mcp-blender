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
- `unity.editor_start`
- `unity.editor_terminate_stuck`
- `unity.hub_install_editor`
- `unity.recover_resume`
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

Presence is lease-like rather than permanent. The local agent normally refreshes
`last_seen_at` about every 20 seconds (including long-running job renewals).
Migration `004_agent_presence_expiry.sql` installs a one-minute `pg_cron` job:
if no heartbeat/renewal arrives for 90 seconds, a non-offline agent becomes
`offline`. The row keeps `last_seen_at`, `last_job_id` and `last_error` for
diagnosis. A database trigger also updates `updated_at` on every agent-row
change, so presence timestamps cannot claim a row is current when it is not.


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

### Unity patch recovery loop

`unity.recover_resume` is the bounded recovery path for a broken Unity Editor
installation. The caller supplies an exact Editor version and optional changeset.
The action only accepts a patch in the project's existing release stream, resolves
the exact Hub executable, upgrades the managed companion, waits for the project to
migrate its `ProjectVersion.txt`, then runs compile, scene summary, physics audit,
spatial audit, Play Mode and capture. Every stage is recorded and the workflow
stops on the first failure. It never falls back to a different Editor version.


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


## Windows resilience model

The OrdaX Agent must remain available without depending on the GitHub runner.

### Primary uptime — external bootstrap + interactive scheduled task

The OrdaX Agent runs through the Windows Scheduled Task named `OrdaX Dev Agent`
under the interactive Windows user, but the task no longer points at a launcher
inside the managed Git checkout.

Installation copies two small bootstrap files to:

`%LOCALAPPDATA%\OrdaX\DevAgent\bootstrap\`

- `ordax-agent-bootstrap.ps1`
- `update_policy.py`

The Scheduled Task executes that external bootstrap. This breaks the circular
dependency where an old/broken agent could not update the very checkout needed
to fix itself.

- The bootstrap retries non-zero agent exits with bounded exponential backoff.
- Before every start it runs the external copy of the same non-refreshing
  tracked-file/index-tree preflight used by `agent.update`.
- It fetches `main` with an explicit
  `refs/heads/main:refs/remotes/origin/main` refspec, so recovery does not depend
  on pre-existing remote-tracking configuration.
- It only accepts fast-forward ancestry.
- It refreshes the editable install only when the semantic install contract
  changes (dependencies, entry points, build backend/package discovery).
- Updated Python is compiled before launch.
- If install/compile validation fails, the checkout is restored to the previous
  known-compilable commit and the prior editable install is restored when needed.
- The legacy `ordax-agent-start.cmd` remains a manual fallback, not the normal
  Scheduled Task entrypoint.
- The watchdog first looks for a successor `ordax_dev_agent.main` process when
  its parent exits; only if no successor exists does it request the enabled,
  non-running `OrdaX Dev Agent` Scheduled Task to start again.

The Agent intentionally runs in the interactive session because visible Blender and Unity workflows must not be launched in Windows Session 0.

### Optional secondary channel — GitHub runner service

If the GitHub self-hosted runner is configured officially as a Windows Service, it can provide an independent CI/recovery channel. OrdaX only hardens an already-supported service configuration; it does not bypass GitHub's Windows runner registration flow.

A runner configured interactively is not a requirement for Agent uptime.

When the self-hosted recovery channel is available, a successful managed
fast-forward also installs/refreshes the external bootstrap and retargets the
Scheduled Task before restarting the agent. This migrates older installations
without requiring the old agent process to know the new update code.

### Local recovery entrypoint

The managed checkout includes:

```powershell
.\scripts\windows\ordax-emergency-recover.ps1
```

It refuses tracked local changes using the shared hash/tree preflight, performs only fast-forward Git updates, compiles the candidate code, rolls back a compile-invalid update, installs/starts the scheduled task and waits for the local health endpoint.

### Installation

Normal one-time Agent bootstrap:

```powershell
.\scripts\windows\ordax-resilience-install.ps1
```

Read-only health report:

```powershell
.\scripts\windows\ordax-resilience-status.ps1
```

The same report is available through the strict action registry as
`agent.resilience_status`. It is intentionally read-only and Windows-only:
the only accepted input is optional `timeout_seconds` (3–30 seconds), and the
agent always executes the repository-owned
`scripts/windows/ordax-resilience-status.ps1`. Callers cannot provide a
script path, command, arguments or shell text. The returned stdout must parse
as a JSON object.

This exposes Scheduled Task state/action, external-bootstrap presence, current
agent processes, local health and GitHub runner-service state without turning
recovery diagnostics into arbitrary remote execution.
