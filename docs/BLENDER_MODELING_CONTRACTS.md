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

`add_modifier` supports BEVEL, SUBSURF, SOLIDIFY, MIRROR and fixed-count linear
ARRAY through
`blender.live_add_modifier`. ARRAY is now
executable.

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

### Array modifier (promoted after Blender smoke)

The `ARRAY` modifier variant has a closed typed plan for fixed-count linear
repetition. It accepts `count` (2–64), a `relative_offset` vector (default
`[1, 0, 0]`) and an optional `constant_offset` vector. When both offsets are
provided, Blender combines them. The planner estimates `evaluated_faces ×
count` and caps the result at 500,000 faces.

Example planning request:

```json
{
  "operation": "add_modifier",
  "object_name": "Rivet",
  "name": "RivetRow",
  "type": "ARRAY",
  "count": 8,
  "relative_offset": [1.25, 0, 0]
}
```

This request can now be sent through the normal typed mutation action.

This variant now returns `status: available` and `executable: true`. The host action
and Blender companion execute it because BlenderBench proves ARRAY modifier creation,
`count=4` runtime-budget evidence, over-limit count rejection, durable trajectory
evidence and source `.blend` integrity on Blender 5.x. The benchmark does not claim
to measure every evaluated spacing outcome. The existing BEVEL, SUBSURF, SOLIDIFY
and MIRROR variants remain available.

### Geometry Nodes surface scatter

`surface_scatter` is available through `blender.live_surface_scatter`. It builds a
closed Geometry Nodes graph with `Distribute Points on Faces`, an index-based hard
instance cap and `Instance on Points`; it does not accept arbitrary nodes or Python.
The request declares a target selector, `source_object_name`, modifier `name`,
`density`, `seed`, `max_instances`, `scale_min`, `scale_max`, `align_to_normal` and
`keep_surface`. Defaults preserve the target surface and align instances to surface
rotation.

Runtime guards cap the target at 200,000 evaluated faces, the source at 100,000
faces, generated instances at 5,000 and projected realized geometry at 2,000,000
faces. The companion measures the actual generated instance count after evaluation
and rejects zero output or any cap violation. Failures remove both the new modifier
and its node group while leaving the source object and previous modifier stack intact.

BlenderBench on Blender 5.2.2 validated fixed seed `37`, an exact 25-instance cap,
overflow rejection, allowed projected geometry budget, durable trajectory evidence
and unchanged source `.blend` hashes. Instances remain non-realized by default.

### Non-destructive Boolean cutter workflow

`boolean_cut_preview` is available through `blender.live_boolean_cut_preview`.
It accepts one target selector plus a workflow `name` and one to eight bounded
profiles. Supported profiles are `box`, `circle`, `slot`, convex `polygon` and
`vent`; vents expand deterministically into repeated slot cutters. Offsets and
rotations are target-local, while the companion creates the cutter objects in a
dedicated preview collection and attaches Exact Difference Boolean modifiers.
No modifier is applied to the target mesh during preview or commit.

The returned `preview_id` drives two workflow actions. `blender.live_boolean_cut_commit`
marks the workflow committed, keeps the Boolean modifiers live and hides the
cutters. `blender.live_boolean_cut_cancel` removes every workflow modifier and
cutter and restores the original modifier stack in one operation. The typed
contract caps a workflow at eight expanded cutters, 64 segments per curved
profile, 16 polygon points, 200,000 evaluated target faces and 12,000 generated
cutter faces. Existing modifiers count against the same stack limit of eight.

BlenderBench on Blender 5.2.2 validated all five profile families in one
seven-cutter preview, rejected an expansion beyond the hard limit, committed the
workflow without applying geometry, cancelled it after commit, verified complete
modifier/cutter rollback, journaled every transition and preserved the source
`.blend` byte-for-byte. The ORDAX Studio WebView bootstrap consumes the same
`blender.live_modeling_schema`, and its MCP / Capacidades view renders the
operation status plus its `commit` and `cancel` workflow actions.

### Mesh repair hints and revision-guarded cleanup

`mesh_quality` now returns `repair_hints` alongside bounded diagnostic samples.
Hints cover loose vertices, non-finite coordinates, zero-length edges, degenerate
faces, wire edges, boundary edges, disconnected components, n-gons and
non-manifold edges. These hints are descriptive rather than blanket defect labels:
open boundaries, multiple components and n-gons can be intentional depending on
the asset.

The first automatic repair is intentionally narrow. When `mesh_quality` runs with
`evaluated=false` and finds truly isolated vertices, it can publish an `auto_fix`
for `blender.live_mesh_cleanup` with repair `remove_loose_vertices`. The fix carries
the base-mesh SHA-256 and diagnosed loose-vertex count. The companion rechecks both
before mutation and refuses stale geometry. It also requires local single-user mesh
data, no shape keys, no modifiers, Object Mode, no render job, and no
animation/constraints.

Cleanup is atomic at the mesh-datablock level: the companion edits a copied mesh,
verifies the exact removed-vertex count, swaps the copy into the object only after
success and restores the original datablock if anything fails. No merge-by-distance,
face dissolve, hole filling, component deletion or retopology is inferred
automatically.

BlenderBench on Blender 5.2.2 validated a nine-vertex fixture containing exactly
one isolated vertex, emitted the revision-guarded repair hint, removed exactly that
one vertex, restored the expected eight-vertex base mesh and rejected a repeated
cleanup using the now-stale pre-repair fingerprint. The source `.blend` remained
byte-for-byte unchanged on disk.

### Degenerate repair preview workflow

Zero-length edges and zero-area faces remain ambiguous enough that ORDAX never
marks them as an automatic cleanup. When a base-mesh `mesh_quality` diagnostic
finds either category and all safety requirements are satisfied, it emits a
`preview_degenerate_dissolve` hint that points to
`blender.live_degenerate_repair_preview`. The workflow uses Blender's Degenerate
Dissolve on a copied candidate mesh with a bounded threshold; the original mesh is
held by a hidden ORDAX backup until the caller chooses `commit` or `cancel`.

The preview requires local single-user mesh data, no shape keys, no modifiers,
Object Mode, no render job, no animation/constraints, a matching base-geometry
SHA-256 and exact diagnosed issue counts. The threshold is capped at `0.001`, the
combined diagnosed zero-length/degenerate element count is capped at `10,000`, and
the target is capped at `200,000` faces. Preview creation fails unless the candidate
strictly reduces the diagnosed defects without increasing either category.

`blender.live_degenerate_repair_commit` refuses a candidate whose fingerprint
changed after preview and then discards the original backup. Conversely,
`blender.live_degenerate_repair_cancel` swaps the exact original datablock back,
verifies its stored SHA-256 before deleting the candidate and only then closes the
workflow. No degenerate repair is auto-applied.

BlenderBench on Blender 5.2.2 validated a fixture with exactly one zero-length edge
and one zero-area face. The candidate reduced both counts from `1 + 1` to `0 + 0`;
cancel restored the exact original geometry fingerprint; a second preview was
committed explicitly; and replaying the old diagnostic fingerprint was rejected as
stale. The source `.blend` on disk remained unchanged.

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

The promotion gate has now been satisfied for `create_primitive`, `add_modifier`,
`surface_scatter`, `boolean_cut_preview` (including commit/cancel transitions),
`mesh_cleanup` (`remove_loose_vertices`) and `degenerate_repair_preview`
(including explicit commit/cancel transitions).
Future modeling mutations must still follow the same fail-closed
process before registration.

## Current real-smoke coverage

`scripts/blender_benchmark.py` continues to exercise the production typed
modeling mutations, the Boolean preview/commit/cancel workflow, revision-guarded
mesh cleanup and the reversible degenerate-repair preview/commit/cancel workflow
through the real companion dispatcher on every BlenderBench run. It keeps
positive/negative controls, exact rollback fingerprints, durable trajectory
evidence, temporary object cleanup and source `.blend` hash protection so later
changes cannot silently weaken the validated behavior.
