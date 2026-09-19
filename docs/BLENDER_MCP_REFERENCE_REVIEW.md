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
6. correct dimensions/contact;
7. capture viewport;
8. compare to reference;
9. repeat until validation passes;
10. assemble validated components;
11. run final contact/structural validation;
12. save artifact.

This loop is the default baseline for future OrdaX Blender generation work.

### Recoverable generation pass

\`blender.live_generation_pass\` is the preferred high-level operation for one
asset/component iteration:

1. create a managed checkpoint;
2. run one approved project script;
3. collect a rich scene snapshot;
4. run declared BVH contact checks;
5. capture the visible viewport;
6. save the accepted .blend when requested.

If the generation script, snapshot, contact audit, required capture, or final
save fails, the pass is rejected. With \`rollback_on_failure=true\` the managed
checkpoint is restored explicitly.

This keeps iteration fast without making failed geometry part of the accepted
asset state.

## 0.7.0 additions from the second reference pass

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
