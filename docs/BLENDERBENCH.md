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
17. all modeling command IDs are present in `trajectory.jsonl`;
18. the temporary smoke object is removed before multiview capture;
19. despite all in-memory modeling operations, the source `.blend` remains
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

The modeling fixture validates the three production typed mutation paths:
`object_transform`, `create_primitive` and `add_modifier`. The same normal
dispatcher operations and runtime guards used by live sessions are exercised in
the benchmark.

The September 20, 2026 benchmark job
`53b9b1ef-81de-406f-966e-576599c257e2` passed on Blender 5.2.2 LTS and was
the promotion evidence for create/modifier. A benchmark failure continues to
block recovery/update of the managed agent instead of allowing an unverified
Blender control layer onto the workstation.
