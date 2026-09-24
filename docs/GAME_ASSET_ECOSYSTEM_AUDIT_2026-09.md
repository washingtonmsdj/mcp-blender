# Game-asset ecosystem audit — 2026-09

Date researched: 2026-09-24

This is the architectural audit behind the OrdaX game-asset tranche. It records
what the repository already had, what was missing, what was implemented in the
current branch, and which external systems should remain optional adapters.

## Repository baseline

Before this tranche, the Device Agent already had a strong general-purpose
Blender/Unity foundation:

- strict action allow-list;
- project-root path confinement;
- bounded subprocess execution;
- Blender Live scene/object/modeling/material/export/capture/checkpoint actions;
- Unity companion/editor/build/import/scene/physics capabilities;
- artifact/reference/Git workflows;
- adapter entry points for optional workstation integrations;
- Linux + Windows CI.

The important gap was not generic Blender control. It was a dedicated
**character/game-asset pipeline**:

- no Mixamo handoff/round-trip contract;
- no armature/skin/action preflight;
- no provider abstraction for modern AI 3D services;
- no engine-specific character export profiles;
- no local generative-workflow bridge;
- no single catalog explaining the 3D ecosystem and constraints.

## Implemented in this tranche

### Blender character preflight

`game_assets.blender_character_preflight` inspects a `.blend` headlessly and
emits machine-readable evidence for:

- geometry counts;
- materials and UVs;
- shape keys;
- skin-weight presence and maximum influences;
- boundary/non-manifold edges;
- object scale;
- armature roots/deform bones;
- actions/frame ranges;
- scene bounds/origin offset;
- Mixamo-style bone naming;
- auto-rig/mapped-rig candidate classification.

Semantic checks that cannot honestly be inferred from metadata remain explicit
manual/visual checks.

### Mixamo

Mixamo is treated as a documented Adobe web handoff, not as an undocumented API.
The pipeline now supports:

1. Blender preflight;
2. clean FBX export;
3. Mixamo upload checklist;
4. returned-FBX ingestion into a clean Blender session;
5. `.blend` preservation of meshes, armatures and actions;
6. engine-specific export.

The round-trip deliberately does not silently rename Mixamo bones.

### Tripo

Typed operations currently exposed:

- text-to-model;
- animation pre-rig check;
- rigging, including documented `spec=mixamo`;
- animation retarget;
- Smart LowPoly.

### Meshy

Typed operations currently exposed:

- Text-to-3D preview;
- PBR refine;
- humanoid rigging;
- Text-to-Motion;
- animation application.

### Hyper3D Rodin Gen-2.5

The branch includes a fixed-endpoint Rodin integration for Text-to-3D with:

- explicit Gen-2.5 tiers;
- Raw/Quad mesh choice;
- quality / face-count control;
- PBR/material mode;
- texture mode;
- T/A-pose conditioning;
- symmetry hint;
- GLB/FBX/OBJ/STL/USDZ output choice;
- correct separation of `subscription_key` (status) and top-level task UUID
  (download manifest);
- body-level API-error checking even when the transport returns HTTP 201.

Credentials remain local environment variables.

### ComfyUI local bridge

The Device Agent now has a loopback-only ComfyUI bridge:

- local system/GPU status with launch `argv` removed from returned context;
- node-class discovery;
- project-versioned API-format workflow execution;
- prompt history retrieval;
- a 5 MiB workflow limit and 2,000-node safety limit;
- no arbitrary remote ComfyUI host.

This is the preferred host for changeable/open local models. Model-specific code
therefore does not have to be permanently welded into the Device Agent.

## External ecosystem findings

### Adobe Mixamo

Use when the goal is fast humanoid auto-rigging and a broad humanoid animation
library. Adobe's documented custom-character flow accepts FBX, OBJ or ZIP, and
already-rigged uploads must use FBX. Its auto-rigger is designed for bipedal
humanoids and benefits from a clean neutral/default pose and centered character.

Decision: **integrated as validated handoff + FBX round-trip**. Do not add browser
scraping or depend on private endpoints.

### Tripo

The current public API is unusually useful to this project because its rigging
operation exposes a `mixamo` skeleton spec, supports FBX/GLB, multiple rig types,
retargeting and low-poly processing.

Decision: **integrated API provider**.

### Meshy

Useful as a broad generation-to-animation pipeline: text/image generation,
refinement/PBR, humanoid rigging, animation and Text-to-Motion.

Decision: **integrated API provider**.

### Hyper3D Rodin

Current Gen-2.5 API is a strong production option because it exposes topology,
face budget, PBR/material controls, T/A-pose conditioning, multiple export
formats and explicit async status/download lifecycle. Hyper3D also publishes its
own MCP server.

Decision: **integrated direct API provider**. Direct API keeps the OrdaX action
contract/project scope under Device Agent control; Hyper3D's MCP remains a
useful external alternative.

### ComfyUI

ComfyUI now documents 3D generation as a first-class workload and includes
3D/animation load/preview/save primitives. Its server exposes stable workflow
queue/history/system routes, and the Comfy organization also publishes a local
MCP server.

Decision: **integrated local workflow host**, not as a bundled model runtime.

### TRELLIS.2

Strengths:

- high-fidelity image-to-3D;
- complex/open/non-manifold topology support;
- PBR material attributes;
- MIT upstream code/model release.

Constraints in the current upstream README:

- tested on Linux;
- NVIDIA GPU with at least 24 GB VRAM required;
- 4B model and CUDA-specific dependencies.

Decision: **optional ComfyUI/local adapter candidate**. Do not make it a Device
Agent install dependency.

### Hunyuan3D 2.1

Upstream includes a FastAPI server with synchronous/asynchronous image-to-3D,
optional texturing, GLB/OBJ output and status/health endpoints.

Important constraint: the upstream source identifies the Hunyuan components as
covered by the Tencent Hunyuan **non-commercial** license. That is materially
different from a permissive production dependency and must be reviewed for the
actual deployment/business use case.

Decision: **optional local adapter/workflow only**; never silently bundle.

### Stable Fast 3D

There is an open local implementation and ComfyUI integration path for fast
single-image asset generation.

Decision: **ComfyUI workflow candidate**, subject to target-device and license
validation.

### DeepMotion Animate 3D

The service publishes a REST API for markerless video-to-3D motion capture,
including full-body tracking, hand/face tracking, multi-person processing,
custom-character retargeting, and FBX/BVH-compatible workflows.

Decision: high-value **future motion-provider adapter** for video reference ->
animation. Keep it separate from geometry generation.

### Rokoko Studio

Rokoko documents a Command API for controlling a running Studio session (for
example record/calibrate/reset/scene info) and exports common motion formats.

Decision: high-value **future workstation adapter** for live/performance capture.
Do not make it part of the core geometry provider module.

### Cascadeur

Cascadeur documents Python scripting and a Python API for automation and custom
commands.

Decision: **future animation-cleanup/physics-assisted adapter** after the base
retarget pipeline is proven.

## Engine pipeline decisions

### Unity

Canonical handoff in this tranche: FBX. Follow-up should install an explicit
`AssetPostprocessor`/ModelImporter preset for generated character folders and
configure Humanoid/Generic Avatar behavior deterministically.

### Unreal Engine

Canonical handoff in this tranche: FBX. Current Unreal documentation identifies
FBX 2020.2 for its FBX skeletal/animation pipeline. A future Unreal companion
should use Editor Python/Interchange for import validation, skeleton assignment,
root motion, morph targets, clips and LODs.

### Godot

Canonical handoff: GLB/glTF 2.0. Godot recommends glTF 2.0 for 3D interchange;
direct `.blend` import works through Blender conversion but makes Blender a
runtime/toolchain dependency on each machine doing the import.

### Web/realtime

Canonical artifact: GLB. Compression must be a separate post-validation pass so
we can compare source vs optimized output.

Khronos KTX2/BasisU is a strong texture-delivery target where
`KHR_texture_basisu` is supported because it reduces transfer/GPU-memory cost.
Geometry compression candidates include Meshopt and Draco depending on the
runtime target.

## Recommended pipeline architecture

```text
reference/prompt/video
        |
        +--> cloud generator (Tripo / Meshy / Rodin)
        |
        +--> local workflow (ComfyUI -> TRELLIS/Hunyuan/SF3D/etc.)
        |
        v
canonical generated asset (prefer GLB; FBX when skeleton/animation requires it)
        |
        v
Blender structural preflight
        |
        +--> geometry/material cleanup
        +--> retopo/low-poly/LOD
        +--> UV/PBR normalization
        |
        v
rig / motion
        |
        +--> Mixamo handoff
        +--> Tripo/Meshy rig/retarget
        +--> future DeepMotion/Rokoko/Cascadeur adapters
        |
        v
Blender visual evidence gate (multiview + representative poses)
        |
        v
engine-specific export
        |
        +--> Unity FBX + importer preset
        +--> Unreal FBX + Interchange/import validation
        +--> Godot GLB
        +--> Web GLB + compression
```

## Next implementation priorities

### P0 — make generated results first-class project artifacts

- provider-result download with strict provider-origin/signed-URL handling;
- SHA-256 + byte size + MIME/extension validation;
- provenance manifest: provider/model/task/prompt/seed/settings/source images;
- auto-ingest GLB/FBX into Blender staging;
- deduplicate identical artifacts by hash.

### P0 — image/multiview generation

- Rodin 1–5 image upload with orientation labels;
- Meshy image-to-3D;
- Tripo image/multiview-to-model;
- project-local image allow-list and upload size caps;
- generation jobs tied to existing reference manifests.

### P1 — character animation normalization

- Mixamo returned-FBX batch ingest;
- action/NLA clip catalog;
- deterministic clip names and frame ranges;
- root-motion extraction/inspection;
- rest-pose and retarget map manifests;
- optional explicit Mixamo bone-name normalization with before/after proof.

### P1 — engine validation companions

- Unity generated-character `AssetPostprocessor` / Avatar preset;
- Unreal Editor Python/Interchange companion;
- Godot import companion;
- per-engine smoke scene that instantiates, animates and captures the asset.

### P1 — optimization

- LOD generation;
- triangle/material/draw-call budgets;
- texture resizing and ORM packing;
- KTX2/BasisU for glTF;
- Meshopt/Draco option matrix;
- engine/device profiles (desktop/mobile/web/VR).

### P2 — motion ecosystem

- DeepMotion API adapter for video mocap;
- Rokoko Studio command/export adapter;
- Cascadeur automation adapter;
- pose/reference-video library tied to project artifacts.

### P2 — quality scoring

Do not produce one opaque “AI quality score”. Keep evidence dimensions separate:

- silhouette/reference similarity;
- topology validity;
- UV/material completeness;
- deformation/skin quality;
- animation foot contact/root drift;
- target-engine import health;
- runtime triangle/material/texture budget;
- visual regression captures.

## Security and reliability rules

1. Never put provider keys in Git/job payloads/artifact manifests.
2. Never allow arbitrary provider URLs when a fixed official endpoint exists.
3. Keep ComfyUI loopback-only unless remote-host authorization is designed
   explicitly.
4. Do not blindly return ComfyUI launch `argv` to model context.
5. Do not scrape Mixamo or automate Adobe credentials through hidden endpoints.
6. Keep input/output paths inside registered project roots.
7. Require explicit overwrite for generated `.blend` outputs.
8. Store provenance for downloaded/generated binary assets.
9. Treat model/provider licensing as a capability constraint, not documentation
   trivia.
10. Prefer small composable actions over a monolithic “make game asset” call.

## Primary sources consulted

Official/public sources used during the 2026-09-24 audit include:

- Adobe Mixamo documentation and FAQ
- Blender 5.2 FBX/glTF/USD documentation and Python API
- Tripo3D OpenAPI documentation
- Meshy API documentation
- Hyper3D Rodin API documentation/changelog
- ComfyUI official docs/source and Comfy MCP repository
- Microsoft TRELLIS.2 repository
- Tencent Hunyuan3D 2.1 repository/API documentation
- Stability AI Stable Fast 3D repository
- DeepMotion Animate 3D API documentation
- Rokoko Studio Command API/export documentation
- Cascadeur Python scripting/API documentation
- Unity ModelImporter documentation
- Unreal Engine FBX/Interchange documentation
- Godot 4.x 3D scene import documentation
- Khronos glTF/KTX2 documentation

Re-verify vendor pricing, model/API versions, licensing and plan requirements at
the time a provider is enabled in production; those change independently of the
Device Agent.
