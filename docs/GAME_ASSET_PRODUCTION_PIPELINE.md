# Canonical game-asset production pipeline

This document is the operational contract for turning prompts, local reference
images, real-world captures and provider task results into traceable Blender and
game-engine assets.

The pipeline is intentionally evidence-first. A cloud provider result is not
considered a durable project asset until it has been downloaded into the project,
hashed, given an OrdaX provenance sidecar and verified before Blender staging or
an engine handoff.

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
                  |               +--> ordax.generated-asset/1 sidecar
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
                  +--> provider/task/hash embedded in scene metadata
                  |
                  +--> structural / character preflight
                  +--> game_assets.blender_runtime_audit
                  +--> optional game_assets.blender_generate_static_lods
                  +--> visual multiview/reference review
                  |
                  +--> rig / Mixamo / animation / retarget
                  |
                  v
engine-specific export / handoff
       Unity: verified copy -> Editor refresh -> model audit
       Unreal: FBX export/import validation
       Godot: GLB import validation
       Web: GLB runtime validation
```

## Source/reference acquisition

### Project-local references

Image-conditioned provider actions consume only JPG/JPEG/PNG files inside the
registered project. The wrapper validates extension and magic bytes and applies
per-image size limits before any upload.

- `game_assets.meshy_submit_images`: 1–4 images.
- `game_assets.tripo_submit_images`: exactly 1 image or four views in the order
  front, left, back, right.
- `game_assets.rodin_submit_images`: 1–5 images, optionally with explicit view
  labels.

A job cannot substitute an arbitrary public URL for these inputs.

### Real-world references through Aleph

For real locations, use the managed `Belluxx/Aleph` adapter. A completed Aleph
capture is retained as canonical evidence. `geo.aleph_blender_stage` derives a
local-metre Blender reference scene from terrain, satellite imagery, OSM and
Street View without modifying the original capture.

## Provider task control plane

Use `game_assets.provider_status` to inspect asynchronous tasks. This action is
intentionally sanitized: it returns task identifiers, state/progress, timestamps,
credit/error fields and other control-plane metadata, but omits model URLs,
thumbnail URLs and other short-lived signed result URLs.

Signed result URLs are consumed internally only by
`game_assets.provider_download`.

## Canonical provider download

`game_assets.provider_download` resolves the provider result server-side and
creates:

```text
generated/asset.glb
generated/asset.glb.ordax.json
```

The sidecar schema is `ordax.generated-asset/1` and records the durable evidence
needed to reproduce and audit the handoff:

- provider;
- operation and task identifier;
- requested format;
- byte count;
- SHA-256;
- redacted source origin/path;
- transfer redirect count;
- provider status metadata where available.

Security/reliability properties:

1. The job does not supply the result URL.
2. Result downloads must use HTTPS.
3. Literal loopback/private/reserved addresses are rejected.
4. Redirects are followed manually with a bounded redirect count and validation
   at each hop.
5. Downloads are streamed with an explicit byte ceiling.
6. Partial downloads use a `.part` file and are removed after failure.
7. Final replacement is atomic.
8. Existing output/sidecar replacement requires `overwrite=true`.
9. Signed URL query strings are not stored in provenance.
10. Provider API credentials are never stored in provenance.

## Integrity gate

Before using a generated provider artifact as a source for editing or engine
handoff, call:

`game_assets.artifact_verify`

It verifies that:

- the sidecar is `ordax.generated-asset/1`;
- the sidecar's relative project path identifies the exact requested file;
- byte size still matches;
- SHA-256 still matches.

This makes accidental/manual replacement of a generated binary visible instead
of silently changing the source used by later Blender or engine work.

## Blender staging

`game_assets.blender_ingest_generated` accepts GLB/glTF, FBX or OBJ and builds a
new project-local `.blend` from a clean Blender factory-startup session.

Provenance is required by default. When present, the resulting scene stores the
source hash, provider, task identifier, source format and operation in custom
scene metadata. The original binary and sidecar remain canonical evidence; the
`.blend` is an editable derivative.

## Structural/character gates

Use `game_assets.blender_character_preflight` when the asset is intended to be a
character. It checks geometry/UVs, skin weights, armatures, actions, scale/origin
and Mixamo-relevant structure.

Use `game_assets.blender_runtime_audit` for any runtime asset. It measures:

- evaluated triangle count;
- vertices;
- material slots/material count;
- texture count, total pixels and largest dimension;
- armature/bone count;
- action count/ranges;
- shape-key count;
- maximum skin influences on a vertex.

Optional limits turn those measurements into an explicit pass/fail budget gate.
The report also identifies a `lod_safe_static_candidate` only when there are no
armatures and no shape keys. This is intentional: automatic decimation should
not silently damage skinned or morph-driven assets.

## Static LOD generation

`game_assets.blender_generate_static_lods` is implemented for static meshes.
Default ratios are `0.5`, `0.25` and `0.1`; callers may request up to five
strictly descending ratios between `0.05` and `0.95`.

The action is deliberately conservative:

- it refuses scenes containing armatures;
- it refuses meshes with shape keys;
- the source `.blend` is never used as the output;
- existing output requires explicit `overwrite=true`;
- current evaluated source geometry is copied first, so existing source
  modifiers are baked into the derivative rather than destructively applied to
  the source scene;
- LOD0 and each reduced level are placed in separate `ORDAX_LOD<n>` collections;
- reduced levels use Blender collapse decimation with triangulated output;
- actual triangle counts are measured after each generated level;
- the derivative stores `ordax.static-lod/1` metadata and a machine-readable
  report.

The default path is therefore:

```text
game_assets.blender_runtime_audit
    -> verify lod_safe_static_candidate
    -> game_assets.blender_generate_static_lods
    -> audit the derivative
    -> visual regression captures
    -> engine export/import
    -> target-engine LOD assignment validation
```

Skinned characters and morph-driven assets are intentionally excluded. They need
a deformation-aware LOD pipeline with skeleton/weight/morph validation before and
after simplification.

## Rig and motion

Humanoid choices currently include:

- Adobe Mixamo validated web handoff and FBX round-trip;
- Tripo rigging/retarget, including Mixamo-compatible skeleton output;
- Meshy humanoid rigging, animation and Text-to-Motion.

Returned FBX assets can be brought back through the Mixamo/FBX ingestion path,
then run through the same preflight, runtime and export gates.

## Unity engine gate

Unity handoff is now an explicit two-stage gate rather than a filesystem copy
being treated as proof of import.

### 1. Verified handoff

`game_assets.unity_import_generated` accepts a canonical generated FBX, OBJ, GLB
or glTF artifact and:

1. verifies its `ordax.generated-asset/1` sidecar and SHA-256 before copying;
2. requires the destination to remain below `Assets/`;
3. copies atomically through the existing idempotent Unity asset copier;
4. preserves the canonical source even when the Editor is unavailable;
5. requests a forced Unity Editor refresh and only reports refresh-confirmed
   handoff when that request succeeds.

The default destination is:

```text
Assets/OrdaX/Generated/<artifact name>
```

A failed refresh is retryable. It is not treated as evidence that Unity imported
the model successfully.

### 2. ModelImporter/runtime audit

After the asset exists below `Assets/`, call:

`game_assets.unity_model_audit`

The Unity companion performs the audit inside the Editor. It forces a synchronous
`AssetDatabase.ImportAsset`, requires an `AssetImporter`, then requires the model
to load as a Unity `GameObject`. The audit measures the imported result rather
than trusting the source file or copy operation.

Evidence returned includes:

- importer type and whether it is a `ModelImporter`;
- global scale;
- Read/Write state;
- animation import state and animation type;
- mesh compression;
- mesh count;
- vertex and triangle counts;
- unique material count;
- animation clip count;
- bone count;
- `LODGroup` count.

The audit fails when Unity cannot create a usable imported model or when no mesh
geometry is present. This deliberately exposes missing GLB/glTF importer support
instead of pretending that copying a `.glb` into `Assets/` was enough. FBX remains
the preferred exchange format for the current Unity character/skeletal path.

The minimum accepted Unity flow is therefore:

```text
game_assets.artifact_verify
    -> game_assets.unity_import_generated
    -> game_assets.unity_model_audit
    -> prefab / LODGroup / collision / animation-specific setup
    -> play-mode or scene validation
```

## Other engine handoff

Current canonical exchange choices:

- Unreal Engine: FBX for the current skeletal/animation pipeline; static LOD
  derivatives should be exported/imported as an explicit LOD set rather than
  treating file export alone as proof that engine LOD assignment succeeded.
- Godot: GLB/glTF 2.0, followed by an engine-side import/runtime gate.
- Web/realtime: GLB/glTF 2.0, followed by runtime loading and visual/performance
  validation.

Engine import validation remains a separate gate everywhere. Export success alone
does not prove avatar mapping, root motion, morph targets, collision, materials,
LOD assignment or runtime budgets are correct in the target engine.

## Component ownership

The game-asset generation pipeline is owned by the independent
`adapter-game-assets` failure domain in the Device Agent component planner.
Aleph remains owned by `adapter-alephgeo`; general Blender Live behavior remains
owned by `adapter-blender`.

This separation matters for future signed component activation and rollback: a
provider/API or local-generation change should not be confused with a core
Blender-control or geospatial-capture update.
