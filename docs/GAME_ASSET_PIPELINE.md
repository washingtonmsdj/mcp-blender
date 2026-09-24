# Game Asset / Character Pipeline

This document describes the first production-oriented game-asset layer of the
OrdaX Device Agent. It is intentionally additive: the existing Blender Live and
Unity capabilities remain unchanged.

## Goals

The pipeline covers four separate concerns instead of mixing them into one
unbounded "AI 3D" action:

1. generate or post-process a 3D asset through an explicitly supported provider;
2. inspect a Blender character before rigging/export;
3. hand a compatible character to Adobe Mixamo without relying on browser
   scraping or undocumented APIs;
4. export a character using engine-specific defaults for Unity, Unreal, Godot,
   or realtime glTF delivery.

All actions remain behind the central `ActionRegistry` allow-list.

## Actions

### `game_assets.providers`

Reports the compiled provider catalog and whether the required API-key
environment variable is present. Secret values are never returned.

Current providers:

- `adobe_mixamo`: supported as a manual, validated handoff;
- `tripo`: generation, pre-rig check, rigging (including `spec=mixamo`),
  retargeting and Smart LowPoly;
- `meshy`: Text-to-3D preview/refine, humanoid rigging, animation and
  Text-to-Motion.

### `game_assets.export_profiles`

Returns the baked export contract for:

- `mixamo` -> FBX
- `unity` -> FBX
- `unreal` -> FBX
- `godot` -> GLB
- `web` -> GLB

Example:

```json
{
  "action": "game_assets.export_profiles",
  "project": "my-game",
  "arguments": {"engine": "godot"}
}
```

### `game_assets.blender_character_preflight`

Starts Blender in background mode on a registered project `.blend` and writes a
structured report under the agent artifact directory.

The report currently checks:

- mesh/armature/action counts;
- vertices, polygons, materials and UV layers;
- shape keys;
- skin weight presence and maximum influences per vertex;
- boundary/non-manifold edges;
- unapplied object scale;
- armature root/deform bone counts;
- Mixamo-style bone naming;
- scene bounds and X/Y origin offset;
- a Mixamo auto-rig/mapped-rig candidate classification.

Checks that require semantic/visual judgment (for example, whether a character
is truly humanoid or in a convincing neutral pose) are deliberately returned as
manual checks rather than fake certainty.

Example:

```json
{
  "action": "game_assets.blender_character_preflight",
  "project": "my-game",
  "arguments": {"blend_file": "characters/scout.blend"}
}
```

### `game_assets.blender_export`

Runs the same headless inspection, selects only meshes/armatures, and exports
with an engine profile.

Examples:

```json
{
  "action": "game_assets.blender_export",
  "project": "my-game",
  "arguments": {
    "blend_file": "characters/scout.blend",
    "engine": "mixamo",
    "output_path": "generated/scout_mixamo.fbx"
  }
}
```

```json
{
  "action": "game_assets.blender_export",
  "project": "my-game",
  "arguments": {
    "blend_file": "characters/scout.blend",
    "engine": "godot",
    "output_path": "generated/scout.glb"
  }
}
```

The output must stay inside the registered project root.

### `game_assets.mixamo_handoff`

Validates the local handoff file before the Adobe Mixamo web step.

Accepted custom-character upload containers are `.fbx`, `.obj` and `.zip`.
When the character is already rigged, the handoff requires `.fbx`.

Example:

```json
{
  "action": "game_assets.mixamo_handoff",
  "project": "my-game",
  "arguments": {
    "source_path": "generated/scout_mixamo.fbx",
    "rigged": false
  }
}
```

The action does **not** upload credentials, automate the Adobe login, or scrape
Mixamo.

### `game_assets.provider_submit`

Submits only pre-defined operations to a hard-coded provider endpoint.

Tripo operations:

- `text_to_model`
- `animate_prerigcheck`
- `animate_rig`
- `animate_retarget`
- `highpoly_to_lowpoly`

Example: create a Mixamo-compatible rig through Tripo's documented rigging API:

```json
{
  "action": "game_assets.provider_submit",
  "project": "my-game",
  "arguments": {
    "provider": "tripo",
    "operation": "animate_rig",
    "original_model_task_id": "TASK_ID",
    "spec": "mixamo",
    "rig_type": "biped",
    "out_format": "fbx",
    "model_version": "v2.5-20260210"
  }
}
```

Meshy operations:

- `text_to_3d_preview`
- `text_to_3d_refine`
- `rigging`
- `text_to_motion`
- `animation`

Example: request an A-pose preview with an explicit polygon budget:

```json
{
  "action": "game_assets.provider_submit",
  "project": "my-game",
  "arguments": {
    "provider": "meshy",
    "operation": "text_to_3d_preview",
    "prompt": "stylized humanoid explorer, clean game character proportions",
    "pose_mode": "a-pose",
    "target_polycount": 30000,
    "ai_model": "latest"
  }
}
```

### `game_assets.provider_status`

Reads one task from a fixed provider route. Meshy requires the originating
operation because its task families have different retrieval endpoints.

## Credentials

Credentials are local workstation configuration, never project configuration:

```powershell
$env:TRIPO_API_KEY = "..."
$env:MESHY_API_KEY = "..."
```

For persistent workstation configuration, set the variables through the normal
OS/secret-management mechanism used by the OrdaX runner. Do not put provider
keys in Git, `agent-settings.json`, generated manifests, prompts, or job
payloads.

## Why Mixamo is a handoff

Adobe documents Mixamo as an Adobe-ID web workflow. The current public
documentation describes supported uploads, auto-rig requirements, download and
the official Blender control-rig add-on, but not a supported public task API.
The Device Agent therefore automates the deterministic local parts:

`Blender preflight -> clean FBX export -> Mixamo handoff -> returned FBX -> engine export`

For end-to-end API automation without a browser, Tripo currently exposes
documented rigging with `spec=mixamo`. That creates a Mixamo-compatible skeleton
through Tripo; it is not an Adobe Mixamo API call.

## Engine guidance

### Unity

Use the FBX profile, then configure `ModelImporter` / Avatar as Humanoid when the
asset is a humanoid character. Unity's editor scripting API can automate this in
a later companion pass.

### Unreal

Use the FBX profile. Unreal's current documented FBX skeletal/animation pipeline
targets FBX 2020.2. The Blender exporter can produce interoperable FBX data but
the final import should still be validated in the target Unreal release,
especially skeleton, root motion, morph targets and clip boundaries.

### Godot

Use GLB. Godot recommends glTF 2.0 for 3D scenes and also supports direct
`.blend` import by asking Blender to convert to glTF. Keeping a generated,
validated GLB artifact avoids requiring every target machine to reproduce the
Blender conversion.

### Web / realtime

Use GLB as the canonical interchange artifact. Perform Meshopt/Draco/KTX2
optimization as a later, measurable pass so visual/regression validation can
compare the uncompressed source with the optimized result.

## Next extensions

The current tranche intentionally establishes safe contracts first. High-value
follow-ups are:

1. signed-result download/import into a project artifact cache;
2. image/multiview-to-3D submissions with project-local image upload;
3. Unity `AssetPostprocessor` presets for Humanoid/Generic rigs;
4. Unreal Editor Python/Interchange companion;
5. Godot editor/import companion;
6. root-motion extraction and Mixamo FBX batch ingestion;
7. animation clip catalog/NLA normalization in Blender;
8. LOD generation and per-engine triangle/material/texture budgets;
9. texture packing (ORM), KTX2/BasisU and glTF compression;
10. optional local-generation adapters (for example ComfyUI-hosted or
    workstation-hosted open models) behind the existing adapter plug-in system.

These should remain separate capabilities so a cloud provider, Blender, or one
game engine can fail without turning the whole pipeline into an opaque
monolith.
