# Engine handoff validation gates

OrdaX treats Blender export, handoff readiness and engine/runtime validation as three different facts. A file existing on disk is never enough to claim that an engine accepted or rendered it correctly.

## Common verified derivative chain

```text
.blend source
  -> game_assets.blender_runtime_audit
  -> optional game_assets.blender_generate_static_lods
  -> game_assets.blender_export_verified
  -> game_assets.engine_export_verify
  -> game_assets.engine_handoff_audit
  -> engine-specific import/runtime validation
```

`game_assets.engine_handoff_audit` re-verifies the `ordax.engine-export/1` sidecar and artifact SHA-256, checks that the target engine matches the artifact extension and export profile, and can optionally require that the current source `.blend` still has the same hash captured at export time.

A successful handoff audit means `ready_for_engine_import=true`. It deliberately returns `validated_in_engine=false` until an engine-specific gate proves otherwise.

## Unity

Unity currently has the complete automated chain:

```text
game_assets.engine_handoff_audit
  -> game_assets.unity_import_engine_export
  -> game_assets.unity_model_audit
  -> game_assets.unity_build_static_lod_prefab   # static LOD derivatives only
```

The static LOD prefab path remains guarded: models with bones, blend shapes, animation clips or an existing LODGroup are refused rather than silently modified.

## Unreal Engine

The verified handoff format is FBX. `game_assets.engine_handoff_audit` validates the export/provenance contract, but the current Device Agent does not yet claim Unreal Editor import success. The next required gate is an Unreal-side import validation that inspects the imported StaticMesh/SkeletalMesh, skeleton/animation assignment and LOD mapping where applicable.

For static LOD assets, exporting a multi-level derivative is not itself proof that Unreal assigned the levels correctly.

## Godot

The verified handoff formats are GLB/glTF 2.0. OrdaX now exposes a real engine-side validation gate:

```text
game_assets.godot_import_validate
```

The action requires a verified `ordax.engine-export/1` artifact targeted to Godot and a project-local directory containing `project.godot`. It then:

1. copies the artifact and provenance sidecar atomically into the Godot project;
2. refuses destinations outside the selected Godot project and requires explicit overwrite;
3. resolves the Godot executable only from `ORDAX_GODOT_BIN` or `godot`/`godot4` on `PATH` — the job cannot supply an arbitrary executable;
4. runs Godot headless in recovery mode with `--import`;
5. runs a temporary OrdaX validation script under Godot itself and requires `ResourceLoader` to load the resulting `res://` resource;
6. reports `engine_validated=true` only after that proof is returned.

Recovery mode is intentionally used to reduce execution of project editor plugins/tool scripts during the validation pass. If import or load fails, the copied derivative is retained for diagnostics while the canonical source artifact is preserved.

## Web / realtime glTF

Web handoff uses GLB/glTF 2.0. For `.glb`, OrdaX also exposes:

```text
game_assets.web_glb_audit
```

This action verifies the export provenance and then parses the GLB container locally. It validates:

- `glTF` magic and GLB version 2;
- declared byte length;
- 4-byte-aligned chunk boundaries;
- first JSON chunk and UTF-8 JSON validity;
- `asset.version == 2.0`;
- scene/node/mesh/material/texture/image/animation/skin counts;
- extension declarations;
- external buffer/image URIs.

By default the Web gate requires a self-contained GLB, so external image or buffer URIs are rejected. A successful structural audit still returns `validated_in_browser=false`; browser loading, visual comparison and performance validation remain the final runtime gate.

## Integrity policy

Historical engine exports remain verifiable even when their source `.blend` later changes. Set `require_current_source=true` on `game_assets.engine_handoff_audit` when the workflow requires the export to be derived from the current source revision rather than merely being a valid historical derivative.
