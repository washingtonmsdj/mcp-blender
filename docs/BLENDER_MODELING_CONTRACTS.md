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


`blender.live_object_transform`, `blender.live_create_primitive` and
`blender.live_add_modifier` are typed modeling mutations available in this phase. It supports one stable selector (`object_name` or
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

## Available create and modifier mutations

`create_primitive` supports cube, sphere and cylinder creation through
`blender.live_create_primitive`.

`add_modifier` supports BEVEL, SUBSURF, SOLIDIFY and MIRROR through
`blender.live_add_modifier`.

Both use the same closed-world planner that powered the staged smoke path. The
runtime preconditions, rollback guarantees and modifier budgets remain enforced:

- creation requires Object Mode, no active render job and a unique object name;
- failed creation cleans partial object/mesh data;
- modifier insertion requires Object Mode, no render job, a local/non-linked mesh
  target and a unique modifier name;
- animated or constrained targets require a dedicated workflow;
- failed modifier insertion removes only the new modifier and preserves the
  existing stack;
- maximum modifier stack: 8;
- maximum evaluated mesh before insertion: 200,000 faces;
- maximum projected SUBSURF mesh: 500,000 faces.

The production promotion is backed by the real BlenderBench run
`53b9b1ef-81de-406f-966e-576599c257e2` executed on September 20, 2026 with
Blender 5.2.2 LTS. That run proved transform positive/negative controls,
successful cube creation, duplicate object-name rejection, successful BEVEL
insertion, duplicate modifier-name rejection, allowed runtime budget, durable
trajectory evidence, UV positive/negative controls, multiview self-comparison
and controlled mutation detection. The benchmark completed with return code 0
and a durable report artifact.

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

The promotion gate has now been satisfied for `create_primitive` and
`add_modifier`. Future modeling mutations must still follow the same fail-closed
process before registration.

## Current real-smoke coverage

`scripts/blender_benchmark.py` continues to exercise all three production
modeling mutations through the real companion dispatcher on every BlenderBench
run. It keeps positive/negative controls, durable trajectory evidence, temporary
object cleanup and source `.blend` hash protection so later changes cannot
silently weaken the validated behavior.
