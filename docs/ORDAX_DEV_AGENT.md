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
