# Blender MCP reference review

Reference reviewed: https://github.com/ahujasid/mcp-for-blender

The external project is MIT-licensed and is used here as an architectural
reference. OrdaX does not vendor it as a runtime dependency.

## What it does well

- persistent interactive Blender companion;
- MCP-first scene and object inspection;
- viewport screenshots as agent feedback;
- richer world-state snapshots (bounds, dimensions, relationships, modifiers,
  animation/material signals);
- broad asset ecosystem (Poly Haven, Poly Pizza, Sketchfab, Hyper3D, Hunyuan3D);
- explicit addon protocol/capability handshake;
- optional AST validation for model-authored Blender Python;
- extensive tests and operational documentation.

## What OrdaX keeps different

OrdaX retains a strict typed action registry and project scoping. Arbitrary
remote shell access is not added.

The external project's arbitrary Blender Python execution is useful for
experimentation, but OrdaX uses approved project scripts and typed live
operations as the normal path. This keeps generation reproducible in Git and
reduces prompt-injection exposure.

OrdaX also keeps its durable job/result/artifact control plane instead of
depending exclusively on an unauthenticated local socket.

## Adopted in OrdaX

### Rich perception

- \`blender.live_scene_snapshot\`
- \`blender.live_object_inspect\`

The snapshot includes world-space AABB, dimensions, parent/children,
collections, materials, modifiers, constraints, mesh counts, animation
metadata and OrdaX semantic properties.

### Geometry acceptance

- \`blender.live_contact_audit\`

Critical object pairs are checked using evaluated Blender mesh BVHs. This is
the final acceptance gate for no-intersection rules; AABBs remain broad-phase
diagnostics only.
### Deterministic quality gates

- \`blender.live_quality_gate\`

One grouped typed operation evaluates geometry contracts without asking the
model to decide whether its own work passed. The verifier set covers dimensions,
bilateral symmetry, dimension ratios, world-AABB containment, and mesh quality.
The mesh-quality contract can bound triangle/ngon/boundary/wire/non-manifold,
loose-vertex, degenerate-face and zero-length-edge counts; it can also require
a minimum quad ratio plus UV and material presence. Every check returns measured
evidence from the live Blender session and refuses client-supplied completion
claims such as `passed`, `ok`, or `result`.

`blender.live_generation_pass` accepts `quality_checks`; a failed deterministic
gate rejects the pass and uses the existing managed rollback when enabled.
### Approved-component revision guards

- `blender.live_object_fingerprints`
- `blender.live_generation_pass` with `protected_objects`

Approved components can be guarded by semantic `ordax_object_id` or by exact
object name. The live companion fingerprints world transform plus evaluated
mesh geometry/topology by default so modifier-driven shape changes are caught;
`evaluated=false` selects the base mesh for time-dependent/simulated cases.
`blender.live_generation_pass` captures the baseline before executing the
generation script and captures the same objects again immediately afterward.
If a protected object was deleted, cannot be resolved, or its fingerprint
changed, the pass is rejected and the managed checkpoint rollback is requested.

Materials and UV data are intentionally outside the default base-geometry lock
so later look-development passes may texture an approved shape without needing
to unlock its geometry. `reset_scene=true` is incompatible with protected
objects because resetting would intentionally destroy the protected state.
### Deterministic multiview evidence

- `blender.live_multiview_capture`
- `blender.live_generation_pass` with `multiview=true` or an options object

The live companion computes evaluated world bounds, creates a temporary
orthographic camera, and captures reproducible views without depending on the
user's active camera. The default bundle is front, back, left, right, top and
three-quarter. Each record includes artifact path, SHA-256, camera transform,
orthographic scale and direction; `multiview.json` records the shared bounds,
objects, resolution, margin, projection and render engine.

When explicit `object_names` are supplied, non-target scene objects are
temporarily hidden from render so component silhouettes can be reviewed without
occlusion. Original render visibility, scene camera, render engine, resolution
and output settings are restored even if a capture fails.

The operation prefers Blender Workbench when the running version exposes it,
falling back to the scene render engine otherwise. Multiview may be a required
`generation_pass` phase, so missing visual evidence can reject and rollback a
pass instead of being silently accepted.
### Multiview baseline comparison

- `blender.multiview_compare`
- `blender.live_generation_pass` multiview options with `baseline_manifest_path`

Comparison is intentionally limited to two OrdaX-generated multiview manifests
inside the same project's managed artifact root. It is not treated as a generic
perceptual score for unrelated reference images. Matching views are compared
at the same resolution by default using normalized RGB mean absolute error, RMS
error and the fraction of pixels with any changed RGB channel. Optional diff
images and world-bounds center/dimension deltas are emitted as evidence.

Thresholds are opt-in. Without `max_mae` or `max_changed_ratio`, comparison is
informational and cannot reject a pass. When thresholds are declared, each view
is evaluated independently and the overall comparison fails if any required
view exceeds a limit. A generation pass can then reject and rollback against an
approved baseline manifest. This preserves human/model agency over what
constitutes an acceptable tolerance instead of hard-coding a universal score.

### Companion capabilities

The visible Blender companion advertises a protocol version and its supported
operations. A clean outdated Blender session may be restarted automatically;
a dirty session is preserved.

### Faster live loop

The companion checks its command inbox at 100 ms intervals while throttling
presence writes to avoid unnecessary filesystem churn.

### External asset discovery

- \`blender.asset_search\`
- \`blender.asset_manifest\`

The first provider is Poly Haven because its assets are CC0 and search does not
require a private API credential. Search and manifest lookup happen in the
agent, not through arbitrary model-authored Blender networking.

## Planned, not blindly copied

- controlled asset download/cache/import with provenance;
- Poly Pizza with license/attribution persistence and CC0-first filtering;
- optional Sketchfab adapter with explicit license checks;
- checkpoints and rollback around modeling passes;
- semantic object transform/edit actions;
- richer material and animation fingerprints;
- trajectory logging for generate -> inspect -> validate -> fix loops.

Hyper3D/Hunyuan-style remote 3D generation may be supported later as optional
providers. They are not core dependencies.

## Explicit non-goals

- arbitrary Python execution as the default remote interface;
- arbitrary shell execution;
- unauthenticated network exposure of Blender control;
- telemetry enabled by default;
- downloading assets without provider/license provenance.

## Default generation loop

1. read the reference contract;
2. generate one component;
3. inspect the component by stable semantic ID/name;
4. run rich scene snapshot;
5. run contact audit for protected pairs;
6. run deterministic geometry quality gates;
7. correct measured dimensions/contact/proportion failures;
8. capture deterministic multiview evidence;
9. compare the same views to the reference/stage baseline;
10. repeat localized corrections until validation passes;
11. assemble validated components;
12. run final contact/structural validation;
13. save artifact.

This loop is the default baseline for future OrdaX Blender generation work.

### Recoverable generation pass

\`blender.live_generation_pass\` is the preferred high-level operation for one
asset/component iteration:

1. create a managed checkpoint;
2. fingerprint declared protected approved objects;
3. run one approved project script;
4. verify protected objects did not change;
5. collect a rich scene snapshot;
6. run declared BVH contact checks;
7. run declared deterministic quality checks;
8. capture deterministic multiview evidence when requested;
9. compare it to an approved OrdaX baseline when requested;
10. capture the visible viewport when requested;
11. save the accepted .blend when requested.

If the generation script, snapshot, contact audit, deterministic quality gate,
required multiview/comparison/capture, or final save fails, the pass is rejected. With \`rollback_on_failure=true\` the managed
checkpoint is restored explicitly.

This keeps iteration fast without making failed geometry part of the accepted
asset state.

## 0.7.3 additions from the second reference pass

The bed benchmark exposed a persistent-Blender correctness issue: Python modules
imported by one generation pass remained in `sys.modules` after a Git sync.
The live companion now invalidates import caches and removes modules loaded from
the registered Blender scripts directory immediately before each `run_script`.
Projects no longer need ad-hoc reload code in their entrypoints.

The reference MCP's newer API/node discovery ideas are now covered natively:

- `blender.live_api_lookup` resolves Blender RNA types, properties, functions
  and `bpy.ops` operators against the running Blender version, including
  parameter/default/enum metadata and typo suggestions;
- `blender.live_api_schema` returns broader RNA class schemas;
- `blender.live_node_schema` reports the sockets that actually exist on a
  Shader, Geometry or Compositor node;
- `property_overrides` may be applied before node introspection so dynamic
  sockets are discovered after mode/data-type changes;
- `blender.live_export` performs controlled GLB/FBX export inside the
  registered project and reports hash/size evidence.

This keeps OrdaX model-agnostic while removing a major source of Blender API
guesswork.


### Benchmark policy

The bed model is a tooling benchmark, not a production asset target. It is used
to stress persistent-session correctness, dependency hot reload, cloth
simulation, BVH validation, viewport evidence, rollback, and export. Once those
behaviors are verified, effort moves back to general Blender/Unity tooling
instead of polishing the benchmark indefinitely.
