# Blender typed modeling contracts

The current OrdaX Blender integration separates **typed contracts** from
**mutation execution**.

This prevents an old Blender implementation from becoming remotely executable
just because its source code existed on a historical branch.

## Available now

`blender.live_modeling_schema` is read-only and returns the supported contracts.

`blender.live_modeling_plan` is also read-only. It accepts one operation and
returns a normalized closed-world plan. Unknown fields and parameters that do
not apply to the chosen primitive/modifier are rejected instead of ignored.
Defaults are materialized in the plan, so a future executor does not have to
reinterpret an underspecified request.

The required flow is:

1. inspect `blender.live_modeling_schema`;
2. call `blender.live_modeling_plan` with one operation;
3. execute only when the returned plan has `executable=true` and a concrete
   action;
4. treat `pending_blender_smoke` plans as non-executable evidence.


`blender.live_object_transform` remains the only typed modeling mutation enabled
in this phase. It supports one stable selector (`object_name` or
`ordax_object_id`) plus one or more of:

- `location`
- `rotation_euler` in radians
- `scale`
- `dimensions`

Validation happens before Blender IPC. Vectors must contain exactly three finite
numbers. Boolean values are not accepted as numbers. Scale and dimensions must
remain strictly positive and within bounded ranges.

The transform action now uses the same planner internally, so unknown fields are
rejected rather than silently ignored.

The visible Blender companion independently re-runs the same shared transform
contract when consuming `object_transform`. Only transport metadata `id` and
`operation` are ignored there; host-only fields or any other unexpected field
are rejected. This is defense in depth: bypassing host validation does not
weaken the Blender-side contract.

## Prepared but deliberately disabled

The contracts also describe:

- `create_primitive`: cube, sphere and cylinder creation;
- `add_modifier`: BEVEL, SUBSURF, SOLIDIFY and MIRROR insertion.

Both report `pending_blender_smoke`. No remote action is registered for either
mutation yet.

The planner also preserves runtime preconditions and rollback guarantees from
the useful part of the historical prototype.

For `create_primitive` the future executor must prove Object Mode, no active
render job and a unique object name. If creation fails after allocating Blender
data, the partial object and mesh must be removed.

For `add_modifier` the future executor must prove Object Mode, no active render
job, a local/non-linked mesh target and a unique modifier name. Animated or
constrained targets require a dedicated workflow instead of silently reusing the
generic modifier path. If insertion/configuration fails, the newly-created
modifier must be removed and the pre-existing modifier stack preserved.

These are contract requirements only; they do not make either mutation
executable.

`add_modifier` also publishes deterministic runtime guards inherited from the
earlier modeling prototype:

- maximum modifier stack: 8;
- maximum evaluated mesh before insertion: 200,000 faces;
- maximum projected SUBSURF mesh: 500,000 faces.

The pure helper `evaluate_modifier_runtime_budget` implements these limits and
is unit-tested, but the planner does **not** accept user-supplied scene metrics as
proof. Modifier count and evaluated face count must come from the live Blender
scene when the executor is eventually enabled.


The earlier implementation is preserved read-only at
`archive/blender-live-session-before-contract-port-2026-09-20`. Its active
`codex/blender-live-session` development branch has been retired after the
useful contracts, runtime guards and rollback semantics were ported to the
current architecture. The archived code remains design evidence only and must
not be merged back wholesale.

One legacy rule is intentionally **not** copied: its transform implementation
required a local, non-linked mesh with no animation/constraints. The current
`blender.live_object_transform` is already a supported general scene-object
operation, so importing that old restriction would be a behavioral regression
rather than a safety improvement.

## Promotion gate

A disabled mutation can become available only after all of the following are
true:

1. the implementation is ported to the current protocol/bundle architecture;
2. host-side contract tests pass;
3. the companion rejects unsupported parameters and unsafe scene state;
4. rollback/checkpoint behavior is verified;
5. a real Blender 5.x smoke executes the operation through the current
   companion dispatcher and validates the resulting scene state;
6. the smoke proves a negative control is rejected, both commands are written to
   the durable trajectory, and the source `.blend` on disk remains unchanged;
7. the normal Bridge CI remains green.

Until that happens, the schema is discoverable but execution remains
unavailable.

This is intentional fail-closed behavior: capability discovery may move ahead of
runtime enablement, but unverified scene mutation may not.

## Current real-smoke coverage

`scripts/blender_benchmark.py` now asks the current companion to run an
optional modeling fixture in a temporary Blender scene. The fixture:

- writes an `object_transform` command to the companion inbox;
- processes it through the same `_process` dispatcher used by live commands;
- requires the positive transform result to be durable;
- sends a zero-scale negative control and requires rejection;
- requires both command IDs in `trajectory.jsonl`;
- relies on BlenderBench's existing before/after SHA-256 check to prove the
  source `.blend` was not saved or overwritten.

This validates the already-supported transform path when the self-hosted Blender
runner is online.

The current companion now also contains **unregistered smoke-only executors** for
`create_primitive` and `add_modifier`. They are intentionally absent from
`CAPABILITIES`, absent from `ActionRegistry`, and accepted by the dispatcher
only when both the modeling-smoke flag and a smoke output directory are active.

BlenderBench exercises these staged paths with:

- successful cube creation;
- duplicate object-name rejection;
- successful BEVEL insertion;
- duplicate modifier-name rejection;
- runtime-budget evidence;
- durable trajectory evidence;
- cleanup of the temporary object before visual capture.

Passing hosted CI is not enough to promote these operations. They remain
`pending_blender_smoke` until the self-hosted Blender 5.x benchmark executes
this exact code successfully. Promotion then requires a separate PR that
registers normal operation names and updates the advertised capabilities.

