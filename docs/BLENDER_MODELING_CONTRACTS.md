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

## Prepared but deliberately disabled

The contracts also describe:

- `create_primitive`: cube, sphere and cylinder creation;
- `add_modifier`: BEVEL, SUBSURF, SOLIDIFY and MIRROR insertion.

Both report `pending_blender_smoke`. No remote action is registered for either
mutation yet.

`add_modifier` also publishes deterministic runtime guards inherited from the
earlier modeling prototype:

- maximum modifier stack: 8;
- maximum evaluated mesh before insertion: 200,000 faces;
- maximum projected SUBSURF mesh: 500,000 faces.

The pure helper `evaluate_modifier_runtime_budget` implements these limits and
is unit-tested, but the planner does **not** accept user-supplied scene metrics as
proof. Modifier count and evaluated face count must come from the live Blender
scene when the executor is eventually enabled.


The historical `codex/blender-live-session` branch contains an earlier
implementation of these operations, but that code targets an older companion
architecture. It is treated as design evidence, not code to merge directly.

## Promotion gate

A disabled mutation can become available only after all of the following are
true:

1. the implementation is ported to the current protocol/bundle architecture;
2. host-side contract tests pass;
3. the companion rejects unsupported parameters and unsafe scene state;
4. rollback/checkpoint behavior is verified;
5. a real Blender 5.x smoke executes the operation and validates the resulting
   scene state;
6. the normal Bridge CI remains green.

Until that happens, the schema is discoverable but execution remains
unavailable.

This is intentional fail-closed behavior: capability discovery may move ahead of
runtime enablement, but unverified scene mutation may not.
