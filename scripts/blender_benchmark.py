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
    script = f"""
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
body = bpy.context.object
body.name = "BenchmarkBody"
body.dimensions = {dimensions!r}
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def uv_probe(name, invalid=False):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(
        [(-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.hide_render = True
    layer = mesh.uv_layers.new(name="UVMap")
    coordinates = (
        [(0.0, 0.0)] * 4
        if invalid
        else [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    )
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            layer.uv[loop_index].vector = coordinates[vertex_index]
    return obj

uv_probe("UVProbe", invalid=False)
uv_probe("UVProbeBad", invalid=True)
bpy.ops.wm.save_as_mainfile(filepath={str(scene)!r})
"""
    scene.parent.mkdir(parents=True, exist_ok=True)
    fixture_script = scene.with_suffix(".fixture.py")
    fixture_script.write_text(script, encoding="utf-8")
    try:
        result = run_process(
            [
                str(blender),
                "--background",
                "--factory-startup",
                "--disable-autoexec",
                "--python-exit-code",
                "1",
                "--python",
                str(fixture_script),
            ],
            timeout_seconds=120,
        )
    finally:
        try:
            fixture_script.unlink()
        except OSError:
            pass

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
            "--ordax-smoke-quality-fixture",
            "--ordax-smoke-modeling-fixture",
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

    valid_quality_path = control_root / "results" / "smoke-quality-valid.json"
    invalid_quality_path = control_root / "results" / "smoke-quality-invalid.json"
    if not valid_quality_path.is_file() or not invalid_quality_path.is_file():
        raise RuntimeError("UV quality fixture did not produce both durable results")
    valid_quality = json.loads(valid_quality_path.read_text(encoding="utf-8-sig"))
    invalid_quality = json.loads(invalid_quality_path.read_text(encoding="utf-8-sig"))
    if not valid_quality.get("ok"):
        raise RuntimeError(
            "UV positive control failed: " + json.dumps(valid_quality, indent=2)
        )
    if invalid_quality.get("ok"):
        raise RuntimeError("UV negative control was incorrectly accepted")
    data["uv_quality"] = {
        "positive_control": True,
        "negative_control_detected": True,
        "valid": valid_quality,
        "invalid": invalid_quality,
    }

    modeling_valid_path = (
        control_root / "results" / "smoke-model-transform.json"
    )
    modeling_invalid_path = (
        control_root / "results" / "smoke-model-invalid.json"
    )
    modeling_create_path = (
        control_root / "results" / "smoke-model-create.json"
    )
    modeling_create_duplicate_path = (
        control_root / "results" / "smoke-model-create-duplicate.json"
    )
    modeling_modifier_path = (
        control_root / "results" / "smoke-model-modifier.json"
    )
    modeling_modifier_duplicate_path = (
        control_root / "results" / "smoke-model-modifier-duplicate.json"
    )
    if not all(
        path.is_file()
        for path in (
            modeling_valid_path,
            modeling_invalid_path,
            modeling_create_path,
            modeling_create_duplicate_path,
            modeling_modifier_path,
            modeling_modifier_duplicate_path,
        )
    ):
        raise RuntimeError(
            "modeling fixture did not produce all durable results"
        )
    modeling_valid = json.loads(
        modeling_valid_path.read_text(encoding="utf-8-sig")
    )
    modeling_invalid = json.loads(
        modeling_invalid_path.read_text(encoding="utf-8-sig")
    )
    modeling_create = json.loads(
        modeling_create_path.read_text(encoding="utf-8-sig")
    )
    modeling_create_duplicate = json.loads(
        modeling_create_duplicate_path.read_text(encoding="utf-8-sig")
    )
    modeling_modifier = json.loads(
        modeling_modifier_path.read_text(encoding="utf-8-sig")
    )
    modeling_modifier_duplicate = json.loads(
        modeling_modifier_duplicate_path.read_text(encoding="utf-8-sig")
    )
    if not modeling_valid.get("ok"):
        raise RuntimeError(
            "modeling positive control failed: "
            + json.dumps(modeling_valid, indent=2)
        )
    if modeling_invalid.get("ok"):
        raise RuntimeError(
            "modeling negative control was incorrectly accepted"
        )

    if not modeling_create.get("ok"):
        raise RuntimeError(
            "primitive creation smoke failed: "
            + json.dumps(modeling_create, indent=2)
        )
    if modeling_create_duplicate.get("ok"):
        raise RuntimeError(
            "duplicate primitive name was incorrectly accepted"
        )
    if not modeling_modifier.get("ok"):
        raise RuntimeError(
            "modifier insertion smoke failed: "
            + json.dumps(modeling_modifier, indent=2)
        )
    if modeling_modifier_duplicate.get("ok"):
        raise RuntimeError(
            "duplicate modifier name was incorrectly accepted"
        )

    created_object = modeling_create.get("object") or {}
    if (created_object.get("mesh") or {}).get("vertices") != 8:
        raise RuntimeError(
            "smoke cube did not expose 8 vertices"
        )

    modifier_object = modeling_modifier.get("object") or {}
    if not any(
        item.get("name") == "SmokeBevel" and item.get("type") == "BEVEL"
        for item in (modifier_object.get("modifiers") or [])
    ):
        raise RuntimeError("smoke BEVEL modifier is missing")
    if not (modeling_modifier.get("runtime_budget") or {}).get("allowed"):
        raise RuntimeError("smoke modifier exceeded runtime budget")

    modeled_object = modeling_valid.get("object") or {}
    if modeled_object.get("location") != [1.25, -0.5, 0.75]:
        raise RuntimeError(
            "modeling fixture location mismatch: "
            + repr(modeled_object.get("location"))
        )
    if modeled_object.get("scale") != [1.0, 1.25, 0.75]:
        raise RuntimeError(
            "modeling fixture scale mismatch: "
            + repr(modeled_object.get("scale"))
        )

    trajectory_path = control_root / "trajectory.jsonl"
    if not trajectory_path.is_file():
        raise RuntimeError("modeling fixture did not create trajectory evidence")
    trajectory_ids = set()
    for line in trajectory_path.read_text(
        encoding="utf-8-sig"
    ).splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        identifier = str(entry.get("id") or "")
        if identifier:
            trajectory_ids.add(identifier)
    if not {
        "smoke-model-transform",
        "smoke-model-invalid",
        "smoke-model-create",
        "smoke-model-create-duplicate",
        "smoke-model-modifier",
        "smoke-model-modifier-duplicate",
    }.issubset(trajectory_ids):
        raise RuntimeError(
            "modeling fixture commands are missing from trajectory evidence"
        )

    data["modeling"] = {
        "positive_control": True,
        "negative_control_detected": True,
        "create_positive": True,
        "create_duplicate_detected": True,
        "modifier_positive": True,
        "modifier_duplicate_detected": True,
        "dispatcher_journaled": True,
        "valid": modeling_valid,
        "invalid": modeling_invalid,
        "create": modeling_create,
        "create_duplicate": modeling_create_duplicate,
        "modifier": modeling_modifier,
        "modifier_duplicate": modeling_modifier_duplicate,
    }

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
        "uv_quality": {
            "positive_control": baseline["uv_quality"]["positive_control"],
            "negative_control_detected": baseline["uv_quality"]["negative_control_detected"],
            "valid_metrics": (
                (baseline["uv_quality"]["valid"].get("checks") or [{}])[0].get("metrics")
            ),
            "invalid_metrics": (
                (baseline["uv_quality"]["invalid"].get("checks") or [{}])[0].get("metrics")
            ),
        },
        "modeling_dispatch": {
            "transform_positive": baseline["modeling"]["positive_control"],
            "transform_negative_detected": baseline["modeling"]["negative_control_detected"],
            "create_positive": baseline["modeling"]["create_positive"],
            "create_duplicate_detected": baseline["modeling"]["create_duplicate_detected"],
            "modifier_positive": baseline["modeling"]["modifier_positive"],
            "modifier_duplicate_detected": baseline["modeling"]["modifier_duplicate_detected"],
            "dispatcher_journaled": baseline["modeling"]["dispatcher_journaled"],
            "location": (
                (baseline["modeling"]["valid"].get("object") or {}).get("location")
            ),
            "scale": (
                (baseline["modeling"]["valid"].get("object") or {}).get("scale")
            ),
            "created_mesh_vertices": (
                ((baseline["modeling"]["create"].get("object") or {}).get("mesh") or {}).get("vertices")
            ),
            "modifier_runtime_budget": baseline["modeling"]["modifier"].get("runtime_budget"),
        },
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
    parser.add_argument(
        "--report-file",
        help="Write the final structured benchmark report to this JSON file.",
    )
    args = parser.parse_args()

    if args.output_dir:
        root = Path(args.output_dir).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        report = run(root)
    else:
        with tempfile.TemporaryDirectory(prefix="ordax-blenderbench-") as raw:
            report = run(Path(raw))

    rendered = json.dumps(report, indent=2)
    if args.report_file:
        report_file = Path(args.report_file).expanduser().resolve()
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
