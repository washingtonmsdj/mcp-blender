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

A successful handoff audit means `ready_for_engine_import=true`. It deliberately returns `validated_in_engine=false` until an engine-specific gate proves otherwise. The result advertises implemented gate names rather than treating export success as engine success.

## Unity

Unity has separate handoff, importer-configuration, structural-model and semantic gates:

```text
game_assets.engine_handoff_audit
  -> game_assets.unity_import_engine_export
  -> game_assets.unity_character_import_configure   # characters when deterministic importer settings are required
  -> game_assets.unity_model_audit
  -> game_assets.unity_semantic_audit
  -> game_assets.unity_build_static_lod_prefab      # static LOD derivatives only
```

`game_assets.unity_model_audit` obtains real evidence from the Unity Editor companion: ModelImporter presence, animation type/import flag, mesh/vertex/triangle/material counts, animation clips, bones, blend shapes and LODGroup count.

`game_assets.unity_character_import_configure` is an explicit mutation gate for one project-local Unity model. It does not install a global `AssetPostprocessor` and it requires `confirm=true`. Typed inputs can control animation type, Avatar setup, an explicit source Avatar for `CopyFromOther`, animation import, `optimizeGameObjects`, curve resampling and mesh readability. The action snapshots the controlled importer values, calls Unity's `SaveAndReimport`, verifies the resulting importer values, and attempts to restore the previous snapshot if reimport fails or Unity normalizes the settings outside the requested contract. After a successful configuration it runs both the standard model audit and the advanced game-asset audit before reporting success.

`CopyFromOther` requires an explicit, different, project-local `source_avatar_path`; `Human`/Humanoid configuration requires either `CreateFromThisModel` or `CopyFromOther`; `None`/`Legacy` are normalized to `NoAvatar`. `is_readable` is never enabled implicitly: Unity keeps a CPU-side copy of readable mesh data, so workflows should request it only when runtime CPU mesh access is actually required.

`game_assets.unity_semantic_audit` layers explicit production requirements over real Editor evidence instead of treating a successful import as game-ready. Baseline workflows can require an animation type (`None`, `Legacy`, `Generic` or `Human`/`Humanoid`), animation import state, minimum mesh/bone/clip/blend-shape/LODGroup counts, and an optional maximum LODGroup count.

When advanced requirements are requested, the action installs the isolated managed `OrdaXGameAssetAgent.cs` companion under `Assets/OrdaX/Editor/`, asks Unity to import it through the existing guarded refresh flow, and communicates through a separate `Library/OrdaXAgent/game-assets` inbox. A pre-existing file is overwritten only when it carries the OrdaX-managed protocol/class markers.

The advanced Unity evidence is read from Unity APIs rather than inferred from naming conventions. It reports:

- `ModelImporter.avatarSetup`;
- Avatar evidence from Avatar sub-assets, `ModelImporter.sourceAvatar` and `Animator.avatar`, deduplicated by Unity instance ID;
- valid Mecanim Avatar and valid humanoid Avatar counts;
- mapped humanoid bone count from `Avatar.humanDescription`;
- animation clips carrying root curves, motion curves, humanoid motion or generic root transforms;
- `Animator`, `MeshRenderer`, `SkinnedMeshRenderer` and Collider counts;
- `LODGroup` count, every LOD level, transition height, assigned renderer count and skinned-renderer count;
- number of LOD levels with no renderer assignment.

Advanced requirements can enforce a valid/humanoid Avatar, root-motion curve evidence, humanoid-motion evidence, a `SkinnedMeshRenderer`, minimum mapped humanoid bones, minimum motion/humanoid clips, minimum LOD levels/renderers/skinned renderers, and non-empty renderer assignment for every LOD level. This also covers Unity's `Copy From Other Avatar` path: the source Avatar is inspected even though Unity does not create a new Avatar sub-asset for that import mode.

Root-motion curve presence is intentionally not treated as a gameplay policy decision. It proves that imported clips contain motion/root evidence; whether a specific runtime Animator should consume root motion remains a separate Play Mode/runtime concern.

The static LOD prefab path remains guarded: models with bones, blend shapes, animation clips or an existing LODGroup are refused rather than silently modified. Deformation-aware character LOD remains a separate path rather than reusing static decimation assumptions.

## Unreal Engine

The verified handoff format is FBX. The automated chain is:

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

## Web / Three.js

Web handoff uses self-contained GLB/glTF 2.0. The implemented chain now has distinct structure, viewer and browser-render gates:

```text
game_assets.engine_handoff_audit
  -> game_assets.web_glb_audit
  -> game_assets.threejs_prepare_viewer          # visual Salvador/WebGPU viewer
  -> game_assets.threejs_runtime_audit           # viewer files/provenance audit
  -> explicit dependency installation if needed  # npm install is not automated
  -> game_assets.threejs_browser_validate        # real browser GLTFLoader + render proof
```

`game_assets.web_glb_audit` verifies export provenance and parses the GLB container locally. It validates the `glTF` magic, GLB version 2, declared byte length, aligned chunk boundaries, JSON validity, `asset.version == 2.0`, scene/node/mesh/material/texture/image/animation/skin counts, extension declarations and external buffer/image URIs. By default it requires a self-contained GLB.

`game_assets.threejs_prepare_viewer` is the visual-experience path for Salvador. It prepares a pinned Three.js/Vite viewer using the shared OrdaX visual-environment contract, `WebGPURenderer`, procedural sky, sun, atmospheric fog, ocean/water and the verified GLB derivative. The generated viewer is deliberately separate from browser validation so visual-environment work can evolve without weakening the immutable asset gate.

`game_assets.threejs_runtime_audit` audits the prepared viewer structure, pinned dependency declarations, visual-environment schema and copied GLB hash. It does not silently run `npm install`: network access and npm lifecycle scripts remain an explicit workstation step.

`game_assets.threejs_browser_validate` is the final generic Web asset runtime gate. It requires the verified original Web GLB plus a project-local installed `three` package, serves only the validation page, Three.js modules and GLB over an ephemeral `127.0.0.1` HTTP server, and launches Chrome/Chromium from `ORDAX_CHROME_BIN` or `PATH`. No CDN or arbitrary browser executable is accepted.

Inside the real browser, `GLTFLoader` loads the GLB and OrdaX records mesh, skinned-mesh, bone, vertex, triangle, material, texture and animation counts. The scene is fitted to a camera, lit, rendered by `WebGLRenderer` into a render target, and read back to measure draw calls, rendered triangles, luminance range and the ratio of pixels that differ from the clear color. The action reports `validated_in_browser=true` and `render_validated=true` only after that browser proof is parsed. Optional requirements can enforce minimum mesh/triangle/animation counts, require a `SkinnedMesh`, and reject nearly blank frames via a minimum visible-pixel ratio.

The browser gate intentionally does not add `--no-sandbox`, does not enable unsafe SwiftShader fallback and does not fetch runtime code from the public Internet. If the workstation cannot provide an acceptable WebGL browser runtime, validation fails rather than weakening those constraints.

The generic browser gate proves that the GLB loads and renders in Three.js. It is not yet a pixel-equivalence test of the full Salvador WebGPU viewer with ocean/sky/atmosphere enabled; that visual-regression layer remains a separate quality gate.

## Integrity policy

Historical engine exports remain verifiable even when their source `.blend` later changes. Set `require_current_source=true` on `game_assets.engine_handoff_audit` when the workflow requires the export to be derived from the current source revision rather than merely being a valid historical derivative.
