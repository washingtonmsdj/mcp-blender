# Preserved historical branches

The active development line is `main`. Historical implementations are kept
under `archive/*` only when their original commit graph still has diagnostic,
design or project-history value.

Archives are **not** alternate update channels and must not be merged back
wholesale. Reuse should be selective: inspect the archived idea, port the useful
behavior into the current architecture, add current tests, and merge through a
normal PR.

## Current archives

### `archive/ordax-engine-before-cleanup-2026-09-17`

Snapshot of the removed Ordax Engine implementation before the repository was
reduced to the Blender/Unity bridge and OrdaX Dev Agent architecture.

Use only for historical comparison.

### `archive/blender-live-session-before-contract-port-2026-09-20`

Original six-commit Blender live-session/modeling experiment.

Useful ideas already ported to `main` include:

- typed modeling schemas;
- closed-world modeling planning;
- transform validation;
- modifier runtime budgets;
- runtime/rollback requirements;
- real object-transform dispatcher smoke coverage.

The archived `bpy/bmesh` executor is not production code and must not be merged
back wholesale.

### `archive/blender-bridge-salvador-prototype-2026-09-17`

Snapshot of the old GitHub-file-queue Blender bridge used during the Salvador
prototype work. The archived branch contains commands/results/previews and
project-specific modeling history, including topographic/elevator studies.

That bridge used a different architecture (GitHub command/result queue, local
relay and optional arbitrary `execute_code`) and is superseded by the typed
OrdaX Dev Agent + Blender Live companion architecture on `main`.

Keep it for project/history inspection only. New automation must use the current
typed action registry and companion bundle.

### `archive/agent-resilience-status-before-salvador-rebase-2026-09-20`

Snapshot of the first `agent.resilience_status` feature branch before the
parallel Salvador onboarding work advanced `main` and the feature was replayed
cleanly on top of that newer architecture.

The production implementation is on `main` starting with Dev Agent 1.18.0.
This archive exists only to preserve the original pre-rebase commit graph; it
contains no capability that should be merged separately.

## Agent-update consolidation archives

The following snapshots preserve superseded update/recovery experiments that
were intentionally not merged wholesale into the final resilience path:

- `archive/agent-update-install-contract-before-consolidation-2026-09-20`
- `archive/agent-update-self-heal-before-consolidation-2026-09-20`
- `archive/recovery-bootstrap-old-agent-before-consolidation-2026-09-20`

Their active `fix/*` refs can be retired even though they contain commits
outside `main`, because the corresponding protected archive points to the exact
same commit. The production replacement is the explicit-refspec update path plus
the external bootstrap under `%LOCALAPPDATA%\OrdaX\DevAgent\bootstrap`.

## Policy

- `main` is the only active integration line.
- `archive/*` is protected from automatic branch hygiene.
- A historical branch is archived before its active ref is retired.
- Automatic hygiene may retire a divergent transient branch only when a
  protected `archive/*` ref points to the exact same commit SHA.
- Otherwise automatic retirement still requires a merged PR and full ancestry
  in `main`.
- No archive is used by `agent.update`, self-hosted recovery or normal CI
  deployment paths.
