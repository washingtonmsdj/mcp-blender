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
13. both modeling command IDs are present in `trajectory.jsonl`;
14. despite the in-memory transform, the source `.blend` remains byte-for-byte
    unchanged on disk.

The benchmark intentionally uses a primitive rather than a production asset.
Its purpose is to detect regressions in transport, Blender runtime behavior,
camera framing, Workbench silhouette rendering, artifact persistence and
comparison metrics without conflating those failures with modeling quality.

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

## CI role

Hosted Bridge CI compiles the benchmark script but cannot validate Blender
runtime behavior. The Windows self-hosted recovery workflow runs BlenderBench
before it is allowed to touch the managed OrdaX agent.

The modeling fixture validates only the already-supported typed transform path.
It does not enable or claim validation for primitive creation or modifier
insertion; those remain `pending_blender_smoke`.

A benchmark failure therefore blocks recovery/update of the managed agent
instead of allowing an unverified Blender control layer onto the workstation.
