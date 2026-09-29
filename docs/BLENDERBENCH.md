# OrdaX BlenderBench

OrdaX BlenderBench is an isolated end-to-end regression test for the Blender
perception and comparison pipeline. It does not open or modify user scenes.

## What it proves

The benchmark creates two temporary `.blend` files:

- baseline: one 2 × 2 × 2 mesh;
- candidate: the same topology with a controlled 3 × 2 × 2 geometry change.

For both files it executes the real `blender_live_companion.py` inside Blender
background mode and captures the deterministic silhouette multiview bundle.

Acceptance requires all of the following:

1. every requested multiview artifact is a real PNG;
2. both manifests are durable and report silhouette mode;
3. the source `.blend` files remain byte-for-byte unchanged after observation;
4. the baseline compared with itself passes at exact thresholds
   (`IoU=1`, `MAE=0`, changed pixels `=0`);
5. the controlled geometry mutation is rejected by the silhouette comparison;
6. the comparison reports at least one failed view;
7. world-bounds evidence reports the known dimension change;
8. a valid 0–1 UV fixture passes zero-area, overlap and shape-distortion gates;
9. a deliberately collapsed UV fixture is rejected as a negative control;
10. a typed `object_transform` command is written to the companion inbox and
    consumed by the real `_process` dispatcher;
11. the positive modeling result is durable and reports the expected location
    and scale;
12. a zero-scale transform is rejected as a modeling negative control;
13. both transform command IDs are present in `trajectory.jsonl`;
14. production `create_primitive` cube creation succeeds and duplicate object names are rejected;
15. production `add_modifier` BEVEL insertion succeeds and duplicate modifier names are rejected;
16. the modifier reports an allowed runtime budget;
17. fixed-count `ARRAY` succeeds, preserves count/budget evidence and rejects an
    over-limit count;
18. `surface_scatter` builds a Geometry Nodes modifier with a fixed seed and an
    exact hard instance cap while preserving instances;
19. scatter overflow is rejected and its runtime budget reports target/source
    faces plus projected instance geometry;
20. `boolean_cut_preview` creates bounded Exact Difference modifiers for box,
    circle, slot, convex polygon and vent profiles without applying the target mesh;
21. a seven-cutter positive control reports an allowed runtime budget while an
    expanded workflow above the eight-cutter cap is rejected;
22. `boolean_cut_commit` preserves live Boolean modifiers while hiding cutters;
23. `boolean_cut_cancel` removes all seven modifiers/cutters and restores the
    pre-preview modifier stack even after commit;
24. a base-mesh `mesh_quality` negative control diagnoses exactly one isolated
    vertex while modifiers are present, reports `modifiers_require_manual_review`
    and does not offer an automatic repair;
25. after modifiers are removed, the same diagnosis emits a revision-guarded
    automatic repair hint;
26. `mesh_cleanup` removes exactly that one loose vertex from a working mesh copy
    and restores the expected eight-vertex base topology;
27. reusing the pre-repair geometry SHA after cleanup is rejected as stale;
28. a base-mesh degenerate fixture diagnoses exactly one zero-length edge and one
    zero-area face, then exposes a preview-only repair hint rather than auto-fix;
29. `degenerate_repair_preview` creates a candidate mesh that reduces the issue
    counts from `1 + 1` to `0 + 0` while retaining the original in an ORDAX backup;
30. `degenerate_repair_cancel` restores the exact original geometry fingerprint
    and removes the candidate/backup state;
31. a second preview can be explicitly committed, after which the candidate becomes
    the production mesh and the hidden original backup is removed;
32. replaying the old diagnostic fingerprint after commit is rejected as stale;
33. explicit-selection Merge by Distance previews vertices `[0,1]`, merges exactly
    one vertex (`6 -> 5`) and verifies all four unselected vertex identities survive;
34. merge cancel restores the exact original fingerprint, commit preserves the reviewed
    candidate, no-op selections are rejected and stale SHA replay is refused;
35. broader topology findings remain descriptive hints rather than implicit edits;
36. all modeling/repair command IDs are present in `trajectory.jsonl`;
37. temporary smoke geometry and repair backup objects are cleaned before capture;
38. despite all in-memory modeling operations, the source `.blend` remains
    byte-for-byte unchanged on disk.

The benchmark intentionally uses a primitive rather than a production asset.
Its purpose is to detect regressions in transport, Blender runtime behavior,
camera framing, Workbench silhouette rendering, artifact persistence and
comparison metrics without conflating those failures with modeling quality.

Fixture scenes are generated through a short temporary `.py` file passed with
Blender's `--python` option (plus `--factory-startup --disable-autoexec`).
The launcher deliberately avoids a large Windows `--python-expr` command line;
the temporary script is deleted in a `finally` block after Blender exits.

## Running locally

From the repository environment:

```powershell
python scripts/blender_benchmark.py
```

To retain all generated scenes, images, manifests, diffs and the comparison
report:

```powershell
python scripts/blender_benchmark.py --output-dir .artifacts/blenderbench
```

## Dev Agent action

The same benchmark is available through the strict action registry as
`blender.benchmark`.

The action accepts only:

- `project` — registered project scope used by the central action policy;
- `timeout_seconds` — integer between 60 and 3600.

It always executes the repository-owned `scripts/blender_benchmark.py`, writes
its working set and `benchmark-report.json` under the OrdaX agent state
directory, and requires all staged modeling evidence before returning success.
No caller-controlled script, command line, executable or output directory is
accepted.

This route exists so an online Dev Agent can run the same real Blender proof even
when the GitHub self-hosted runner service is unavailable.

## CI role

Hosted Bridge CI compiles the benchmark script but cannot validate Blender
runtime behavior. The Windows self-hosted recovery workflow runs BlenderBench
before it is allowed to touch the managed OrdaX agent.

The modeling fixture validates the production typed mutation paths
`object_transform`, `create_primitive`, `add_modifier` (including fixed-count
`ARRAY`) and `surface_scatter`, plus the non-destructive `boolean_cut_preview` â†’
`boolean_cut_commit` â†’ `boolean_cut_cancel` workflow, revision-guarded
`mesh_cleanup`, reversible `degenerate_repair_preview` â†’ commit/cancel and
explicit-selection `merge_by_distance_preview` â†’ commit/cancel workflows. The same normal dispatcher operations and runtime guards used by live
sessions are exercised in the benchmark.

The September 20, 2026 benchmark job
`53b9b1ef-81de-406f-966e-576599c257e2` passed on Blender 5.2.2 LTS and was
the promotion evidence for create/modifier. On September 28, 2026, the same
Blender 5.2.2 benchmark promoted `surface_scatter` after proving a fixed seed of
37, an exact 25-instance cap, overflow rejection, projected-geometry budget
evidence, dispatcher journaling and unchanged source `.blend` hashes. The same
September 28 Blender 5.2.2 run then promoted the Boolean cutter workflow after
validating box/circle/slot/polygon/vent profiles, a seven-cutter preview, expansion
overflow rejection, non-destructive commit and complete cancel rollback. Later on
September 28, 2026, BlenderBench also promoted `mesh_cleanup` after a base-mesh
quality check first proved that modifiers block auto-fix, then emitted a
fingerprint-bound isolated-vertex repair after those modifiers were removed; the
companion removed exactly one vertex and rejected the stale pre-repair fingerprint.
On September 29, 2026, BlenderBench promoted the degenerate-repair workflow using
a fixture with one zero-length edge and one zero-area face: preview reduced both
counts to zero, cancel restored the exact original SHA-256, explicit commit retained
the candidate, and the old diagnostic hash was rejected as stale. Every command was
journaled and the source `.blend` stayed unchanged. The September 29 Blender 5.2.2
run also promoted explicit-selection Merge by Distance: `[0,1]` merged one vertex
from a six-vertex fixture, all four unselected identities survived preview/commit,
cancel restored the original SHA, no-op selection was rejected and stale replay failed.
A benchmark failure continues
to block recovery/update of the managed agent instead of allowing an unverified
Blender control layer onto the workstation.
