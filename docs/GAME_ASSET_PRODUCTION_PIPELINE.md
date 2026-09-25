# Canonical game-asset production pipeline

This document is the operational contract for turning prompts, local reference
images, real-world captures and provider task results into traceable Blender and
game-engine assets.

The pipeline is evidence-first. A provider result is not a durable project asset
until it has been downloaded into the project, hashed, given an OrdaX provenance
sidecar and verified. Likewise, a Blender export is not considered an engine
artifact until its source snapshot and exported bytes have their own provenance.

## End-to-end flow

```text
project references / Aleph capture / prompt
                  |
                  +--> Meshy / Tripo / Rodin
                  |       |
                  |       +--> sanitized task status
                  |       +--> canonical provider download
                  |               |
                  |               +--> SHA-256
                  |               +--> ordax.generated-asset/1
                  |
                  +--> ComfyUI local workflow
                  |
                  v
project-local generated source artifact
                  |
                  +--> game_assets.artifact_verify
                  |
                  v
game_assets.blender_ingest_generated
                  |
                  +--> clean Blender staging file
                  +--> provider/task/hash in scene metadata
                  |
                  +--> game_assets.blender_runtime_audit
                  +--> optional game_assets.blender_generate_static_lods
                  +--> visual/reference review
                  |
                  v
game_assets.blender_export_verified
                  |
                  +--> engine artifact
                  +--> ordax.engine-export/1
                  +--> game_assets.engine_export_verify
                  |
                  v
engine handoff
       Unity: verified copy -> Editor refresh -> model audit -> optional LODGroup prefab
       Unreal: verified FBX export -> engine import validation
       Godot: verified GLB export -> engine import validation
       Web: verified GLB export -> runtime validation
```

## Project-local references

Image-conditioned provider actions consume only JPG/JPEG/PNG files inside the
registered project. The wrapper validates extension and magic bytes and applies
per-image size limits before upload.

- `game_assets.meshy_submit_images`: 1–4 images.
- `game_assets.tripo_submit_images`: exactly 1 image or four views in the order
  front, left, back, right.
- `game_assets.rodin_submit_images`: 1–5 images, optionally with explicit view
  labels.

A job cannot substitute an arbitrary public URL for these inputs.

For real locations, use the managed Aleph adapter. A completed Aleph capture is
retained as canonical evidence. `geo.aleph_blender_stage` derives a local-metre
Blender reference scene from terrain, satellite imagery, OSM and Street View
without modifying the original capture.

## Provider control plane and canonical download

Use `game_assets.provider_status` for asynchronous task state. The action returns
control-plane metadata but omits signed model/thumbnail URLs.

`game_assets.provider_download` resolves the provider result server-side and
creates a local artifact plus an `ordax.generated-asset/1` sidecar, for example:

```text
generated/asset.glb
generated/asset.glb.ordax.json
```

The sidecar records provider, operation/task ID, format, byte count, SHA-256 and
redacted transfer metadata. Downloads are HTTPS-only, streamed with byte limits,
redirects are bounded/validated, partial files are removed after failure and
replacement requires explicit `overwrite=true`.

## Generated-asset integrity gate

Before using a provider artifact, call `game_assets.artifact_verify`. It checks:

- sidecar schema;
- exact project-relative artifact identity;
- byte size;
- SHA-256.

`game_assets.blender_ingest_generated` then creates a new project-local `.blend`
from a clean Blender session and embeds provider/task/hash information into the
scene. The original provider binary and sidecar remain canonical evidence.

## Runtime audit

`game_assets.blender_runtime_audit` measures evaluated runtime characteristics:

- triangles and vertices;
- material slots/materials;
- texture count, total pixels and largest dimension;
- armatures/bones;
- actions;
- shape keys;
- maximum skin influences.

Optional limits make these metrics a pass/fail budget. The report only marks an
asset as `lod_safe_static_candidate` when there are no armatures and no shape
keys.

## Static LOD generation in Blender

`game_assets.blender_generate_static_lods` is deliberately static-only. Default
ratios are `0.5`, `0.25`, `0.1`; callers may request up to five strictly
descending ratios from `0.05` to `0.95`.

Safety rules:

- refuse armatures;
- refuse shape keys;
- never overwrite the source `.blend`;
- require explicit overwrite for an existing derivative;
- bake the evaluated source geometry into the derivative first;
- create LOD0 and reduced levels in distinct `ORDAX_LOD<n>` collections;
- name generated objects with `_LOD<n>` suffixes so engine importers can recover
  level membership even when Blender collection structure is not preserved;
- measure actual post-decimation triangle counts;
- store `ordax.static-lod/1` metadata/report.

Skinned characters and morph-driven assets remain excluded until a separate
deformation-aware simplification path can validate skeletons, weights and morphs
before and after reduction.

## Verified Blender engine exports

Use `game_assets.blender_export_verified` for the engine-facing derivative. It
wraps the existing engine-specific Blender exporter but adds a durable content
contract.

The action:

1. hashes the source `.blend` before export;
2. exports to a temporary file in the target directory;
3. re-hashes the source and refuses promotion if it changed during export;
4. hashes the exported artifact;
5. creates an `ordax.engine-export/1` sidecar with engine target, source snapshot,
   artifact identity, export profile and report;
6. promotes the temporary artifact and sidecar only after success;
7. requires `overwrite=true` for replacement.

`game_assets.engine_export_verify` validates the artifact bytes against this
sidecar. A later edit to the source `.blend` does **not** invalidate a historical
export: verification returns `source_current_matches=false` while retaining the
source snapshot hash that produced the artifact.

Typical files:

```text
exports/prop_lods.fbx
exports/prop_lods.fbx.ordax.json
```

## Unity verified handoff

There are two provenance-aware Unity handoff routes:

- `game_assets.unity_import_generated` for a canonical provider artifact using
  `ordax.generated-asset/1`;
- `game_assets.unity_import_engine_export` for a Blender-derived artifact using
  `ordax.engine-export/1`.

The engine-export route additionally requires `engine == "unity"` in provenance,
so a valid Unreal-targeted FBX cannot silently enter the Unity path.

Both routes copy atomically below `Assets/`, preserve the canonical source on
Editor failure and can require a confirmed Unity refresh. The default destination
is `Assets/OrdaX/Generated/<artifact>`.

## Unity ModelImporter/runtime audit

After the file is below `Assets/`, call `game_assets.unity_model_audit`.

The companion forces synchronous `AssetDatabase.ImportAsset`, requires an
`AssetImporter`, requires the model to load as a `GameObject`, and measures the
result Unity actually imported:

- importer type / `ModelImporter` presence;
- global scale;
- Read/Write state;
- animation import state/type;
- mesh compression;
- mesh count;
- vertex/triangle counts;
- unique material count;
- animation clip count;
- bone count;
- blend-shape count;
- existing `LODGroup` count.

This gate exposes missing model-import support instead of treating a successful
filesystem copy as a successful Unity import.

## Unity static LODGroup prefab

`game_assets.unity_build_static_lod_prefab` builds a prefab only after a fresh
model audit confirms that the imported asset is suitable for the static path.

It refuses:

- bones/skinned content;
- blend shapes;
- animation clips;
- an existing `LODGroup` on the source model;
- renderers not associated with a `_LOD<n>` hierarchy;
- missing/gapped levels (levels must be contiguous from `_LOD0`);
- invalid/non-descending transition thresholds;
- implicit overwrite of an existing prefab.

The companion instantiates the imported model, maps renderer groups by `_LOD<n>`,
adds one `LODGroup`, assigns strictly descending transition heights, recalculates
bounds, saves a prefab and destroys the temporary scene instance.

The canonical static Unity chain is:

```text
game_assets.blender_runtime_audit
    -> game_assets.blender_generate_static_lods
    -> game_assets.blender_runtime_audit       # audit derivative
    -> visual/reference review
    -> game_assets.blender_export_verified     # engine=unity, usually FBX
    -> game_assets.engine_export_verify
    -> game_assets.unity_import_engine_export
    -> game_assets.unity_model_audit
    -> game_assets.unity_build_static_lod_prefab
    -> scene/play-mode validation
```

This order is intentional. No export, filesystem copy or prefab save is accepted
as evidence for a later gate by itself.

## Rig and motion

Humanoid choices currently include:

- Adobe Mixamo validated web handoff and FBX round-trip;
- Tripo rigging/retarget, including Mixamo-compatible skeleton output;
- Meshy humanoid rigging, animation and Text-to-Motion.

Returned FBX assets can be brought back through the Mixamo/FBX ingestion path and
run through the same preflight/runtime/export gates. Character LOD generation is
not yet automated because static decimation rules are intentionally insufficient
for deformable geometry.

## Other engines

Current exchange choices:

- Unreal Engine: FBX for current skeletal/animation exchange; use verified export
  provenance and add a separate Unreal import/LOD validation gate.
- Godot: GLB/glTF 2.0 followed by an engine-side import/runtime gate.
- Web/realtime: GLB/glTF 2.0 followed by runtime load, visual and performance
  validation.

Engine export success never proves avatar mapping, root motion, morph targets,
collision, materials, LOD assignment or runtime budgets in the target engine.

## Component ownership

The game-asset pipeline is owned by the independent `adapter-game-assets` failure
domain in the Device Agent component planner. Aleph remains owned by
`adapter-alephgeo`; general Blender Live behavior remains owned by
`adapter-blender`.

This separation keeps future signed component activation/rollback scoped to the
correct failure domain rather than treating provider, engine and Blender-control
changes as one monolith.
