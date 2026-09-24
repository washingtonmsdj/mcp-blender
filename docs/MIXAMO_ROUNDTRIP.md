# Mixamo round-trip

The OrdaX Device Agent treats Adobe Mixamo as a supported handoff rather than an
undocumented browser/API integration.

## End-to-end flow

```text
source .blend
  -> game_assets.blender_character_preflight
  -> game_assets.blender_export(engine=mixamo)
  -> game_assets.mixamo_handoff
  -> Adobe Mixamo web auto-rig / animation selection
  -> downloaded FBX inside the registered project
  -> game_assets.blender_import_fbx
  -> validated .blend with rig/actions preserved
  -> game_assets.blender_export(engine=unity|unreal|godot|web)
```

For a fully API-driven alternative, Tripo's documented `animate_rig` operation
can be submitted through `game_assets.provider_submit` with `spec=mixamo`. This
produces a Mixamo-compatible skeleton through Tripo; it is not an Adobe Mixamo
API call.

## Import a returned FBX

Place the downloaded FBX inside the registered project and execute:

```json
{
  "action": "game_assets.blender_import_fbx",
  "project": "my-game",
  "arguments": {
    "source_path": "generated/mixamo/scout_walk.fbx",
    "output_blend": "characters/scout_walk.blend"
  }
}
```

The action:

- accepts only a project-local `.fbx`;
- applies a 1 GiB local input safety limit;
- uses a clean Blender factory-startup session;
- imports FBX animation data;
- requires explicit `overwrite=true` before replacing an existing `.blend`;
- saves a new `.blend` inside the registered project;
- emits an artifact report with mesh, armature, action and Mixamo-rig counts.

It does not rename Mixamo bones automatically. Silent renaming can break skin
bindings, animation curves, retarget maps or engine avatars, so normalization
should be a separate explicit operation with before/after validation.

## What still needs visual validation

Automation can verify structure but should not pretend it can prove deformation
quality from metadata alone. After ingestion, render/capture representative
poses and inspect at least:

- shoulders and clavicles;
- elbows and knees at deep bends;
- wrists/fingers when present;
- hips/crotch;
- feet contacting the floor;
- clothing/armor intersections;
- root-motion behavior;
- facial blendshapes/morph targets when the asset uses them.

The existing OrdaX Blender capture/multiview and reference-review actions are the
right evidence layer for this visual gate.
