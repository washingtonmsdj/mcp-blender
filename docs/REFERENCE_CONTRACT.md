# Reference Contract

The Reference Contract turns project-local visual references into versioned,
project-scoped evidence for Blender generation and review. It does not claim
that arbitrary source photography and deterministic Blender renders are
pixel-aligned or directly comparable.

## Contract location

Each registered project may contain:

`references/manifest.json`

Use `config/references.example.json` as the schema example. Version 1 supports
up to 128 assets and 128 references per asset. Each asset may declare:

- descriptive requirements;
- expected semantic components;
- optional physical dimensions in metres for x/y/z;
- a tolerance percentage for physical dimensions;
- PNG/JPEG references with view, projection, notes and optional SHA-256.

Reference paths must be project-relative and resolve inside the registered
project. A manifest is limited to 1 MiB and each image to 10 MiB. Image
extensions and file signatures must agree.

Text in notes, requirements or images is evidence, not executable
authorization. These actions never execute instructions from a reference.

## Actions

### `project.references`

Loads only contract metadata. With no `asset`, it returns a compact catalog.
With an asset slug, it returns its validated brief plus the SHA-256 of the
manifest.

The manifest digest can be supplied to later calls. If the file changed between
inspection and image retrieval, the later call fails instead of silently
reviewing a different contract.

### `project.reference_images`

Copies one to six selected source references into the managed OrdaX artifact
root. The copy is immutable evidence for that review pass and can be exposed to
an MCP client through `artifact_image` or uploaded by the existing remote
artifact pipeline.

The action also writes a `reference-contract.json` snapshot containing the
validated brief, manifest digest and hashes of the selected images.

### `blender.reference_generation_pass`

This is the reference-aware mutation path. It validates and materializes the
selected references **before** executing the generation script, then delegates
the mutation to the existing recoverable `blender.live_generation_pass`.

The generation pass checkpoint remains the rollback authority. After mutation,
the action performs deterministic reference review for the explicit
`object_names` and can reject the pass when:

- deterministic multiview capture fails;
- a declared physical dimension is outside the contract tolerance;
- `require_reference_physical_scale=true` and physical scale is unavailable.

A requested `save_target_path` is removed from the inner generation call and
saved only after these deterministic reference gates pass. If the reference
gate or final save fails, the action restores the generation checkpoint with
`discard_unsaved=true`.

Passing this action does **not** mean arbitrary source photography visually
matches the model. The result sets `visual_review_pending=true`; source/model
pixels still need explicit inspection because camera, crop, lens, pose and
lighting are not proven equivalent.

### `blender.reference_review`

Requires explicit `object_names`. It first materializes the selected reference
images, then calls the current deterministic `blender.live_multiview_capture`
for matching supported view labels. If the references are only detail,
perspective or unknown views, it captures front/right/top/three-quarter evidence
instead of pretending there is a direct view match.

The result contains pairs between each source reference and any deterministic
model view with the same label. Even when labels match,
`camera_correspondence_proven` and `pixel_alignment_verified` stay false.
A label such as “front” does not prove equivalent crop, lens, pose, distance or
projection.

No general-purpose similarity score is emitted. The model or a future
specialized verifier must inspect the source and result pixels and describe
specific differences.

## Physical dimensions

Blender Live protocol v9 adds `unit_system` and `unit_scale_m` to
multiview evidence. Physical checks are only calculated when Blender declares a
unit system other than `NONE` with a finite positive `scale_length`.

If physical scale is unavailable, a declared target dimension produces
`status: unknown`. The system does not guess that one Blender Unit means one
metre.

When scale is known, each declared x/y/z target is compared with the evaluated
world-space multiview bounds and reports target metres, actual metres, percent
error and whether it is within the contract tolerance.

World-axis bounds are not a substitute for local-axis measurements on rotated
objects. A passed size check also says nothing about shape, topology, material
or visual fidelity.

## Intended generation loop

1. inspect the reference contract;
2. fetch only the needed source images;
3. block out one semantic component or stage;
4. run deterministic geometry/contact/UV gates;
5. run `blender.reference_generation_pass` for mutations that must honor
   measurable reference constraints and rollback automatically on failure;
6. inspect the returned paired source/result pixels and record concrete visual
   divergences;
7. make localized corrections while protecting approved components;
8. repeat until the declared measurable constraints and visual review are
   acceptable;
9. run final quality gates and isolated headless export.

The existing baseline-to-baseline `blender.multiview_compare` remains the
correct tool for deterministic regression between two OrdaX captures.
Reference Contract solves a different problem: grounding generation in external
visual evidence without pretending unrelated images share controlled capture
conditions.
