# Engine handoff validation gates

OrdaX treats Blender export, handoff readiness, engine import/load and semantic quality validation as different facts. A file existing on disk is never enough to claim that an engine accepted or interpreted it correctly.

## Common verified derivative chain

```text
.blend source
  -> game_assets.blender_runtime_audit
  -> optional game_assets.blender_generate_static_lods
  -> game_assets.blender_export_verified
  -> game_assets.engine_export_verify
  -> game_assets.engine_handoff_audit
  -> engine-specific import/runtime validation
  -> engine-specific semantic quality gate when applicable
```

`game_assets.engine_handoff_audit` re-verifies the `ordax.engine-export/1` sidecar and artifact SHA-256, checks that the target engine matches the artifact extension and export profile, and can optionally require that the current source `.blend` still has the same hash captured at export time.

A successful handoff audit means `ready_for_engine_import=true`. It deliberately returns `validated_in_engine=false` until an engine-specific gate proves otherwise. The result now advertises the implemented `next_gate` and, when one exists, a `semantic_gate` rather than conceptual placeholder names.

## Unity

Unity currently has the automated chain:

```text
game_assets.engine_handoff_audit
  -> game_assets.unity_import_engine_export
  -> game_assets.unity_model_audit
  -> game_assets.unity_build_static_lod_prefab   # static LOD derivatives only
```

The model audit inspects importer and geometry/animation signals in the Unity Editor. The static LOD prefab path remains guarded: models with bones, blend shapes, animation clips or an existing LODGroup are refused rather than silently modified.

## Unreal Engine

The verified handoff format is FBX. The automated chain is now:

```text
game_assets.engine_handoff_audit
  -> game_assets.unreal_import_validate
  -> game_assets.unreal_asset_audit
```

`game_assets.unreal_import_validate` requires a verified `ordax.engine-export/1` FBX targeted to Unreal and a project-local `.uproject`. It resolves the editor command only from `ORDAX_UNREAL_EDITOR_CMD` or Unreal Editor command names on `PATH`; the job cannot provide an arbitrary executable. The destination is restricted to a normalized `/Game/...` package path and dot path segments are rejected.

Validation runs the supported Unreal Python commandlet flow in unattended/null-RHI mode. The temporary script creates an `AssetImportTask`, enables automated import, imports through `AssetTools`, requires non-empty imported object paths, loads each imported object through `EditorAssetLibrary`, saves the loaded assets, and prints an OrdaX proof containing the object paths and classes. OrdaX accepts the proof only when every returned object is under the requested destination path. Only then does the action report `engine_validated=true`.

`game_assets.unreal_asset_audit` is the semantic quality gate for already-imported assets. It loads explicit `/Game/...` objects through the Unreal Editor and reports, depending on asset type:

- StaticMesh: LOD count, triangles, vertices, sections and UV channel count per LOD, material count, BodySetup presence and simple collision-shape count;
- SkeletalMesh: LOD count, assigned Skeleton, bone count, material count, morph-target count and PhysicsAsset assignment;
- AnimationAsset: assigned Skeleton and play length;
- Skeleton: bone count.

Optional requirements can fail the gate even when the asset loads successfully: expected Unreal classes, minimum static/skeletal LOD counts, required skeletal Skeleton, required PhysicsAsset, required animation Skeleton and required simple StaticMesh collision. This separation prevents “imported successfully” from being treated as “game-ready”.

The Unreal project's Python Scripting Plugin must already be enabled, as required by Epic's command-line Python workflow.

## Godot

The verified handoff formats are GLB/glTF 2.0. Godot uses an integrated import/load/semantic gate:

```text
game_assets.engine_handoff_audit
  -> game_assets.godot_import_validate
```

The action requires a verified `ordax.engine-export/1` artifact targeted to Godot and a project-local directory containing `project.godot`. It then:

1. copies the artifact and provenance sidecar atomically into the Godot project;
2. refuses destinations outside the selected Godot project and requires explicit overwrite;
3. resolves the Godot executable only from `ORDAX_GODOT_BIN` or `godot`/`godot4` on `PATH` — the job cannot supply an arbitrary executable;
4. runs Godot headless in recovery mode with `--import`;
5. requires `ResourceLoader` to load the resulting `res://` resource;
6. when the imported resource is a `PackedScene`, instantiates it headless and walks the scene tree;
7. reports mesh instances/surfaces/materials/blend shapes, Skeleton3D/bone totals, AnimationPlayer/animation totals, collision objects and CollisionShape3D nodes;
8. reports `engine_validated=true` only after load and semantic proof are returned.

Optional requirements can enforce minimum MeshInstance3D count, minimum Skeleton3D count, minimum total bones, minimum animations and the presence of an assigned collision shape. A scene may therefore be loadable but still fail semantic production requirements.

Recovery mode is intentionally used to reduce execution of project editor plugins/tool scripts during the validation pass. If import or load fails, the copied derivative is retained for diagnostics while the canonical source artifact is preserved.

## Web / realtime glTF

Web handoff uses GLB/glTF 2.0. The next implemented gate is:

```text
game_assets.engine_handoff_audit
  -> game_assets.web_glb_audit
  -> browser runtime validation   # not implemented yet
```

`game_assets.web_glb_audit` verifies the export provenance and then parses the GLB container locally. It validates:

- `glTF` magic and GLB version 2;
- declared byte length;
- 4-byte-aligned chunk boundaries;
- first JSON chunk and UTF-8 JSON validity;
- `asset.version == 2.0`;
- scene/node/mesh/material/texture/image/animation/skin counts;
- extension declarations;
- external buffer/image URIs.

By default the Web gate requires a self-contained GLB, so external image or buffer URIs are rejected. A successful structural audit still returns `validated_in_browser=false`; actual Three.js/browser loading, render/visual proof and performance validation remain the final runtime gate.

## Integrity policy

Historical engine exports remain verifiable even when their source `.blend` later changes. Set `require_current_source=true` on `game_assets.engine_handoff_audit` when the workflow requires the export to be derived from the current source revision rather than merely being a valid historical derivative.
