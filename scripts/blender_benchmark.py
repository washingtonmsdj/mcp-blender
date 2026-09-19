"""OrdaX BlenderBench: isolated end-to-end geometry/perception regression.

Creates two temporary Blender scenes, runs the real live companion multiview
implementation in background Blender, then verifies that:
- a baseline compared with itself is identical;
- a controlled geometry mutation is detected by silhouette IoU and bounds;
- source .blend files are not modified by observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_blender_unity.config import find_blender
from mcp_blender_unity.process import run_process
from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


def _create_scene(blender: Path, scene: Path, dimensions: tuple[float, float, float]) -> None:
    expression = (
        "import bpy; "
        "bpy.ops.wm.read_factory_settings(use_empty=True); "
        "bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0)); "
        "obj=bpy.context.object; obj.name='BenchmarkBody'; "
        f"obj.dimensions={dimensions!r}; "
        "bpy.context.view_layer.objects.active=obj; "
        "bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); "
        f"bpy.ops.wm.save_as_mainfile(filepath={str(scene)!r})"
    )
    result = run_process(
        [
            str(blender),
            "--background",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python-expr",
            expression,
        ],
        timeout_seconds=120,
    )
    if not result["ok"]:
        raise RuntimeError(json.dumps(result, indent=2))


def _run_companion_smoke(
    blender: Path,
    companion: Path,
    scene: Path,
    root: Path,
    label: str,
) -> dict:
    state_root = root / "state"
    project_artifacts = state_root / "artifacts" / "bench"
    control_root = root / "control" / label
    output_dir = project_artifacts / label
    scripts_root = root / "automation" / "blender"
    scripts_root.mkdir(parents=True, exist_ok=True)

    before = hashlib.sha256(scene.read_bytes()).hexdigest()
    result = run_process(
        [
            str(blender),
            "--background",
            str(scene),
            "--python-exit-code",
            "1",
            "--python",
            str(companion),
            "--",
            "--ordax-control-root",
            str(control_root),
            "--ordax-project-root",
            str(root),
            "--ordax-scripts-root",
            str(scripts_root),
            "--ordax-artifacts-root",
            str(project_artifacts),
            "--ordax-project-slug",
            "bench",
            "--ordax-smoke-output-dir",
            str(output_dir),
            "--ordax-smoke-mode",
            "silhouette",
            "--ordax-smoke-width",
            "384",
            "--ordax-smoke-height",
            "384",
        ],
        timeout_seconds=180,
    )
    if not result["ok"]:
        raise RuntimeError(json.dumps(result, indent=2))

    result_path = control_root / "results" / "smoke.json"
    if not result_path.is_file():
        raise RuntimeError(f"missing durable companion result: {result_path}")
    data = json.loads(result_path.read_text(encoding="utf-8-sig"))
    if not data.get("ok"):
        raise RuntimeError(json.dumps(data, indent=2))

    after = hashlib.sha256(scene.read_bytes()).hexdigest()
    if before != after:
        raise AssertionError(f"companion modified source scene: {scene}")

    manifest = Path(data["manifest"])
    if not manifest.is_file():
        raise AssertionError(f"multiview manifest missing: {manifest}")
    for artifact in data.get("artifacts", []):
        path = Path(artifact["artifact"])
        if not path.is_file() or not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise AssertionError(f"invalid PNG artifact: {path}")
    return data


def _registry(root: Path) -> ActionRegistry:
    config = AgentConfig(
        agent_name="blenderbench",
        supabase_url=None,
        publishable_key=None,
        poll_seconds=5.0,
        state_dir=root / "state",
        agent_repo_path=root,
        hordax_path=root,
        bridge_path=root,
        projects={
            "bench": {
                "path": str(root),
                "apps": ["blender"],
                "blender": {"scripts_dir": "automation/blender"},
            }
        },
        default_project="bench",
    )
    return ActionRegistry(config)


def run(root: Path) -> dict:
    blender = find_blender()
    if not blender:
        raise RuntimeError("Blender not installed")
    blender = Path(blender)

    companion = (
        Path(__file__).resolve().parents[1]
        / "ordax_dev_agent"
        / "assets"
        / "blender_live_companion.py"
    )
    baseline_scene = root / "baseline.blend"
    candidate_scene = root / "candidate.blend"

    _create_scene(blender, baseline_scene, (2.0, 2.0, 2.0))
    _create_scene(blender, candidate_scene, (3.0, 2.0, 2.0))

    baseline = _run_companion_smoke(
        blender, companion, baseline_scene, root, "baseline"
    )
    candidate = _run_companion_smoke(
        blender, companion, candidate_scene, root, "candidate"
    )

    agent = _registry(root)
    identical = agent.execute(
        "blender.multiview_compare",
        {
            "project": "bench",
            "baseline_manifest_path": baseline["manifest"],
            "candidate_manifest_path": baseline["manifest"],
            "min_silhouette_iou": 1.0,
            "max_mae": 0.0,
            "max_changed_ratio": 0.0,
        },
    )
    if not identical.ok:
        raise AssertionError(
            "baseline self-comparison failed: "
            + json.dumps(identical.data, indent=2)
        )

    mutation = agent.execute(
        "blender.multiview_compare",
        {
            "project": "bench",
            "baseline_manifest_path": baseline["manifest"],
            "candidate_manifest_path": candidate["manifest"],
            "min_silhouette_iou": 0.99,
            "write_diff_images": True,
        },
    )
    if mutation.ok:
        raise AssertionError("controlled geometry mutation was not detected")
    if not mutation.data.get("failed_views"):
        raise AssertionError("mutation comparison reported no failed views")

    dimension_error = (
        mutation.data.get("bounds", {}).get("absolute_dimension_error") or []
    )
    if not dimension_error or max(dimension_error) < 0.9:
        raise AssertionError(
            "controlled dimension change was not reflected in bounds evidence"
        )

    return {
        "ok": True,
        "blender": str(blender),
        "baseline_manifest": baseline["manifest"],
        "candidate_manifest": candidate["manifest"],
        "baseline_views": [item["view"] for item in baseline["artifacts"]],
        "self_comparison": {
            "passed": identical.data.get("comparison_passed"),
            "views": identical.data.get("views"),
        },
        "mutation_detection": {
            "detected": not mutation.ok,
            "failed_views": mutation.data.get("failed_views"),
            "bounds": mutation.data.get("bounds"),
            "report": mutation.data.get("report"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        help="Keep benchmark files in this directory instead of a temporary directory.",
    )
    args = parser.parse_args()

    if args.output_dir:
        root = Path(args.output_dir).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        report = run(root)
    else:
        with tempfile.TemporaryDirectory(prefix="ordax-blenderbench-") as raw:
            report = run(Path(raw))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
