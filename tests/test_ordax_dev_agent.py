import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from PIL import Image, ImageDraw

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.main import _start_local_watchdog, _upload_result_artifacts
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class AgentActionRegistryTests(unittest.TestCase):
    def make_config(self, root: Path) -> AgentConfig:
        return AgentConfig(
            agent_name="test-agent",
            supabase_url=None,
            publishable_key=None,
            poll_seconds=5.0,
            state_dir=root / "state",
            agent_repo_path=root / "agent",
            hordax_path=root / "hordax",
            bridge_path=root / "bridge",
        )

    def test_unknown_action_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            result = registry.execute("shell.exec", {"command": "whoami"})
            self.assertFalse(result.ok)
            self.assertIn("not allowed", result.summary)

    def test_status_lists_only_registered_actions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            result = registry.execute("agent.status", {})
            self.assertTrue(result.ok)
            self.assertIn("agent.update", result.data["actions"])
            self.assertIn("agent.resilience_repair", result.data["actions"])
            self.assertIn("unity.compile", result.data["actions"])
            self.assertIn("blender.run_python", result.data["actions"])
            self.assertIn("blender.live_start", result.data["actions"])
            self.assertIn("blender.live_status", result.data["actions"])
            self.assertIn("blender.live_material_apply", result.data["actions"])
            self.assertIn("blender.live_create_camera", result.data["actions"])
            self.assertIn("blender.live_create_light", result.data["actions"])
            self.assertIn("blender.live_scene_presentation", result.data["actions"])
            self.assertIn("blender.live_import_asset", result.data["actions"])
            self.assertIn("blender.live_animate_transform", result.data["actions"])
            self.assertIn("blender.live_batch", result.data["actions"])
            self.assertIn("blender.live_viewport_proxy", result.data["actions"])
            self.assertIn("blender.live_bake_work_proxy", result.data["actions"])
            self.assertIn("blender.live_inspect", result.data["actions"])
            self.assertIn("blender.live_scene_snapshot", result.data["actions"])
            self.assertIn("blender.live_scene_reset", result.data["actions"])
            self.assertIn("blender.live_object_inspect", result.data["actions"])
            self.assertIn("blender.live_object_fingerprints", result.data["actions"])
            self.assertIn("blender.live_contact_audit", result.data["actions"])
            self.assertIn("blender.live_quality_gate", result.data["actions"])
            self.assertIn("blender.live_modeling_schema", result.data["actions"])
            self.assertIn("blender.live_modeling_plan", result.data["actions"])
            self.assertIn("blender.live_object_transform", result.data["actions"])
            self.assertIn("blender.live_object_metadata", result.data["actions"])
            self.assertIn("blender.live_api_schema", result.data["actions"])
            self.assertIn("blender.live_api_lookup", result.data["actions"])
            self.assertIn("blender.live_node_schema", result.data["actions"])
            self.assertIn("blender.live_export", result.data["actions"])
            self.assertIn("blender.export_headless", result.data["actions"])
            self.assertIn("unity.cli_status", result.data["actions"])
            self.assertIn("unity.pipeline_install", result.data["actions"])
            self.assertIn("unity.pipeline_catalog", result.data["actions"])
            self.assertIn("unity.pipeline_command", result.data["actions"])
            self.assertIn("unity.asset_inventory", result.data["actions"])
            self.assertIn("unity.asset_import", result.data["actions"])
            self.assertIn("unity.editor_diagnostics", result.data["actions"])
            self.assertIn("unity.recover_resume", result.data["actions"])
            self.assertIn("blender.live_checkpoint_create", result.data["actions"])
            self.assertIn("blender.live_checkpoint_list", result.data["actions"])
            self.assertIn("blender.live_checkpoint_restore", result.data["actions"])
            self.assertIn("blender.live_trajectory", result.data["actions"])
            self.assertIn("blender.live_generation_pass", result.data["actions"])
            self.assertIn("blender.live_result", result.data["actions"])
            self.assertIn("blender.live_run_script", result.data["actions"])
            self.assertIn("blender.live_capture", result.data["actions"])
            self.assertIn("blender.live_multiview_capture", result.data["actions"])
            self.assertIn("blender.live_save", result.data["actions"])
            self.assertIn("blender.live_stop", result.data["actions"])
            self.assertIn("blender.asset_search", result.data["actions"])
            self.assertIn("blender.asset_manifest", result.data["actions"])
            self.assertIn("blender.multiview_compare", result.data["actions"])
            self.assertIn("project.references", result.data["actions"])
            self.assertIn("project.reference_images", result.data["actions"])
            self.assertIn("blender.reference_review", result.data["actions"])
            self.assertIn("blender.reference_generation_pass", result.data["actions"])
            self.assertIn("blender.reference_decision", result.data["actions"])
            self.assertIn("blender.live_create_primitive", result.data["actions"])
            self.assertIn("blender.live_add_modifier", result.data["actions"])
            self.assertNotIn("shell.exec", result.data["actions"])


    def test_resilience_repair_verifies_periodic_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            repo = config.agent_repo_path
            installer = repo / "scripts" / "windows" / "ordax-agent-bootstrap-install.ps1"
            installer.parent.mkdir(parents=True)
            installer.write_text("Write-Output '{}'", encoding="utf-8")
            registry = ActionRegistry(config)

            repaired = ActionResult(True, "ok", {"stdout": "{}"})
            verified = ActionResult(
                True,
                "ready",
                {
                    "resilience": {
                        "scheduled_task": {
                            "exists": True,
                            "triggers": [
                                {"repetition_interval": ""},
                                {"repetition_interval": "PT1M"},
                            ],
                        }
                    }
                },
            )
            with patch("ordax_dev_agent.agent_actions.sys.platform", "win32"), patch(
                "ordax_dev_agent.agent_actions._run", return_value=repaired
            ), patch.object(
                registry, "agent_resilience_status", return_value=verified
            ):
                result = registry.execute("agent.resilience_repair", {})

            self.assertTrue(result.ok, f"{result.summary}: {result.data}")
            self.assertEqual(2, result.data["trigger_count"])
            self.assertEqual(1, result.data["maintenance_trigger_count"])

    def test_modeling_plan_normalizes_available_cube_action(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_modeling_plan",
                {
                    "operation": "create_primitive",
                    "name": "HullBlock",
                    "primitive": "cube",
                },
            )

            self.assertTrue(result.ok)
            self.assertTrue(result.data["executable"])
            self.assertEqual("available", result.data["execution"])
            self.assertEqual(
                "blender.live_create_primitive",
                result.data["action"],
            )
            self.assertEqual(
                {
                    "name": "HullBlock",
                    "primitive": "cube",
                    "location": [0.0, 0.0, 0.0],
                    "size": 2.0,
                },
                result.data["arguments"],
            )

    def test_modeling_plan_rejects_inapplicable_modifier_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_modeling_plan",
                {
                    "operation": "add_modifier",
                    "object_name": "Hull",
                    "name": "Mirror",
                    "type": "MIRROR",
                    "width": 0.1,
                },
            )

            self.assertFalse(result.ok)
            self.assertIn("unsupported field(s) for MIRROR", result.summary)

    def test_modeling_plan_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_modeling_plan",
                {
                    "operation": "object_transform",
                    "object_name": "Hull",
                    "location": [0, 0, 0],
                    "code": "anything",
                },
            )

            self.assertFalse(result.ok)
            self.assertIn("unsupported field(s): code", result.summary)

    def test_object_transform_rejects_unknown_fields_before_ipc(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.execute(
                    "blender.live_object_transform",
                    {
                        "object_name": "Hull",
                        "location": [0, 0, 0],
                        "unexpected": 1,
                    },
                )

            self.assertFalse(result.ok)
            self.assertIn("unsupported field(s): unexpected", result.summary)
            live.assert_not_called()

    def test_modeling_schema_exposes_validated_mutations_as_available(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute("blender.live_modeling_schema", {})

            self.assertTrue(result.ok)
            tools = result.data["tools"]
            self.assertEqual("available", tools["object_transform"]["status"])
            self.assertEqual(
                "blender.live_object_transform",
                tools["object_transform"]["action"],
            )
            self.assertEqual("available", tools["create_primitive"]["status"])
            self.assertEqual(
                "blender.live_create_primitive",
                tools["create_primitive"]["action"],
            )
            self.assertEqual("available", tools["add_modifier"]["status"])
            self.assertEqual(
                "blender.live_add_modifier",
                tools["add_modifier"]["action"],
            )
            self.assertEqual(
                "available",
                result.data["mutation_policy"]["create_primitive"],
            )
            self.assertEqual(
                "available",
                result.data["mutation_policy"]["add_modifier"],
            )

    def test_create_primitive_normalizes_and_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_create_primitive",
                    {
                        "name": "Block",
                        "primitive": "cube",
                        "size": 2,
                    },
                )

        self.assertTrue(result.ok)
        self.assertEqual("create_primitive", result.data["operation"])
        self.assertEqual(
            {
                "name": "Block",
                "primitive": "cube",
                "location": [0.0, 0.0, 0.0],
                "size": 2.0,
            },
            result.data["payload"],
        )

    def test_add_modifier_normalizes_and_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_add_modifier",
                    {
                        "object_name": "Block",
                        "name": "Edges",
                        "type": "bevel",
                    },
                )

        self.assertTrue(result.ok)
        self.assertEqual("add_modifier", result.data["operation"])
        self.assertEqual(
            {
                "object_name": "Block",
                "name": "Edges",
                "type": "BEVEL",
                "width": 0.05,
                "segments": 2,
            },
            result.data["payload"],
        )

    def test_promoted_modeling_mutations_remain_closed_world(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                create = registry.execute(
                    "blender.live_create_primitive",
                    {
                        "name": "Block",
                        "primitive": "cube",
                        "code": "anything",
                    },
                )
                modifier = registry.execute(
                    "blender.live_add_modifier",
                    {
                        "object_name": "Block",
                        "name": "Edges",
                        "type": "BEVEL",
                        "levels": 2,
                    },
                )

        self.assertFalse(create.ok)
        self.assertIn("unsupported field(s): code", create.summary)
        self.assertFalse(modifier.ok)
        self.assertIn("unsupported field(s) for BEVEL", modifier.summary)
        live.assert_not_called()

    def test_object_transform_rejects_nonfinite_boolean_and_invalid_scale(self) -> None:
        invalid_payloads = [
            {"object_name": "Hull", "location": [0.0, float("nan"), 0.0]},
            {"object_name": "Hull", "rotation_euler": [0.0, True, 0.0]},
            {"object_name": "Hull", "scale": [1.0, 0.0, 1.0]},
            {"object_name": "Hull", "scale": [1.0, float("inf"), 1.0]},
            {"object_name": "Hull", "dimensions": [1.0, -0.1, 1.0]},
        ]

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                for payload in invalid_payloads:
                    with self.subTest(payload=payload):
                        result = registry.execute(
                            "blender.live_object_transform",
                            payload,
                        )
                        self.assertFalse(result.ok)
                live.assert_not_called()

    def test_object_transform_normalizes_valid_numeric_values(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_object_transform",
                    {
                        "object_name": "Hull",
                        "location": [1, 2.5, -3],
                        "scale": [1, 2, 1],
                    },
                )

            self.assertTrue(result.ok)
            self.assertEqual("object_transform", result.data["operation"])
            self.assertEqual([1.0, 2.5, -3.0], result.data["payload"]["location"])
            self.assertEqual([1.0, 2.0, 1.0], result.data["payload"]["scale"])

    def test_quality_gate_rejects_model_supplied_completion_claim(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_quality_gate",
                {
                    "checks": [
                        {
                            "type": "dimensions",
                            "object_name": "Bed",
                            "expected": [2.0, 1.6, 0.5],
                            "passed": True,
                        }
                    ]
                },
            )

            self.assertFalse(result.ok)
            self.assertIn("cannot provide its own completion claim", result.summary)

    def test_quality_gate_accepts_uv_quality_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))

            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={"operation": operation, "checks": payload["checks"]},
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_quality_gate",
                    {
                        "checks": [
                            {
                                "type": "uv_quality",
                                "object_name": "UVProbe",
                                "max_zero_area_faces": 0,
                                "max_overlap_pairs": 0,
                            }
                        ]
                    },
                )

            self.assertTrue(result.ok)
            self.assertEqual("quality_gate", result.data["operation"])
            self.assertEqual("uv_quality", result.data["checks"][0]["type"])

    def test_quality_gate_rejects_unsupported_check_type(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_quality_gate",
                {"checks": [{"type": "looks_good"}]},
            )

            self.assertFalse(result.ok)
            self.assertIn("type must be one of", result.summary)


    def test_object_fingerprints_reject_duplicate_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_object_fingerprints",
                {
                    "selectors": [
                        {"object_name": "Frame"},
                        {"object_name": "Frame"},
                    ]
                },
            )

            self.assertFalse(result.ok)
            self.assertIn("duplicate fingerprint selector", result.summary)


    def test_multiview_rejects_duplicate_views_before_blender_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_multiview_capture",
                {"views": ["front", "front"]},
            )

            self.assertFalse(result.ok)
            self.assertIn("views must be unique", result.summary)

    def test_multiview_rejects_invalid_resolution_before_blender_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_multiview_capture",
                {"width": 32, "height": 768},
            )

            self.assertFalse(result.ok)
            self.assertIn("between 128 and 4096", result.summary)


    def test_multiview_compare_identical_bundle_has_zero_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            artifact_root = root / "state" / "artifacts" / "hordax"
            baseline_dir = artifact_root / "baseline"
            candidate_dir = artifact_root / "candidate"
            baseline_dir.mkdir(parents=True)
            candidate_dir.mkdir(parents=True)

            baseline_image = baseline_dir / "front.png"
            candidate_image = candidate_dir / "front.png"
            Image.new("RGB", (16, 16), (20, 40, 60)).save(baseline_image)
            Image.new("RGB", (16, 16), (20, 40, 60)).save(candidate_image)

            baseline_manifest = baseline_dir / "multiview.json"
            candidate_manifest = candidate_dir / "multiview.json"
            manifest_bounds = {
                "dimensions": [2.0, 1.0, 0.5],
                "center": [0.0, 0.0, 0.25],
            }
            baseline_manifest.write_text(
                json.dumps({
                    "views": [{"view": "front", "artifact": str(baseline_image)}],
                    "bounds": manifest_bounds,
                }),
                encoding="utf-8",
            )
            candidate_manifest.write_text(
                json.dumps({
                    "views": [{"view": "front", "artifact": str(candidate_image)}],
                    "bounds": manifest_bounds,
                }),
                encoding="utf-8",
            )

            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.multiview_compare",
                {
                    "baseline_manifest_path": str(baseline_manifest),
                    "candidate_manifest_path": str(candidate_manifest),
                    "max_mae": 0.0,
                    "max_changed_ratio": 0.0,
                },
            )

            self.assertTrue(result.ok)
            self.assertTrue(result.data["comparison_passed"])
            self.assertEqual(0.0, result.data["views"][0]["mae"])
            self.assertEqual(0.0, result.data["views"][0]["changed_pixel_ratio"])

    def test_multiview_compare_rejects_bundle_above_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            artifact_root = root / "state" / "artifacts" / "hordax"
            baseline_dir = artifact_root / "baseline"
            candidate_dir = artifact_root / "candidate"
            baseline_dir.mkdir(parents=True)
            candidate_dir.mkdir(parents=True)

            baseline_image = baseline_dir / "front.png"
            candidate_image = candidate_dir / "front.png"
            Image.new("RGB", (16, 16), (0, 0, 0)).save(baseline_image)
            Image.new("RGB", (16, 16), (255, 255, 255)).save(candidate_image)

            baseline_manifest = baseline_dir / "multiview.json"
            candidate_manifest = candidate_dir / "multiview.json"
            baseline_manifest.write_text(
                json.dumps({
                    "views": [{"view": "front", "artifact": str(baseline_image)}],
                    "bounds": {"dimensions": [1, 1, 1], "center": [0, 0, 0]},
                }),
                encoding="utf-8",
            )
            candidate_manifest.write_text(
                json.dumps({
                    "views": [{"view": "front", "artifact": str(candidate_image)}],
                    "bounds": {"dimensions": [1, 1, 1], "center": [0, 0, 0]},
                }),
                encoding="utf-8",
            )

            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.multiview_compare",
                {
                    "baseline_manifest_path": str(baseline_manifest),
                    "candidate_manifest_path": str(candidate_manifest),
                    "max_mae": 0.05,
                    "max_changed_ratio": 0.05,
                },
            )

            self.assertFalse(result.ok)
            self.assertFalse(result.data["comparison_passed"])
            self.assertEqual(["front"], result.data["failed_views"])


    def test_multiview_rejects_unknown_capture_mode_before_blender_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.live_multiview_capture",
                {"mode": "wireframe"},
            )

            self.assertFalse(result.ok)
            self.assertIn("material or silhouette", result.summary)

    def test_silhouette_multiview_compare_enforces_iou_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            artifact_root = root / "state" / "artifacts" / "hordax"
            baseline_dir = artifact_root / "baseline-silhouette"
            candidate_dir = artifact_root / "candidate-silhouette"
            baseline_dir.mkdir(parents=True)
            candidate_dir.mkdir(parents=True)

            baseline_image = baseline_dir / "front.png"
            candidate_image = candidate_dir / "front.png"

            baseline_canvas = Image.new("RGB", (16, 16), (255, 255, 255))
            ImageDraw.Draw(baseline_canvas).rectangle(
                [4, 4, 11, 11],
                fill=(0, 0, 0),
            )
            baseline_canvas.save(baseline_image)

            candidate_canvas = Image.new("RGB", (16, 16), (255, 255, 255))
            ImageDraw.Draw(candidate_canvas).rectangle(
                [5, 5, 10, 10],
                fill=(0, 0, 0),
            )
            candidate_canvas.save(candidate_image)

            baseline_manifest = baseline_dir / "multiview.json"
            candidate_manifest = candidate_dir / "multiview.json"
            baseline_manifest.write_text(
                json.dumps({
                    "mode": "silhouette",
                    "views": [{"view": "front", "artifact": str(baseline_image)}],
                    "bounds": {"dimensions": [1, 1, 1], "center": [0, 0, 0]},
                }),
                encoding="utf-8",
            )
            candidate_manifest.write_text(
                json.dumps({
                    "mode": "silhouette",
                    "views": [{"view": "front", "artifact": str(candidate_image)}],
                    "bounds": {"dimensions": [1, 1, 1], "center": [0, 0, 0]},
                }),
                encoding="utf-8",
            )

            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "blender.multiview_compare",
                {
                    "baseline_manifest_path": str(baseline_manifest),
                    "candidate_manifest_path": str(candidate_manifest),
                    "min_silhouette_iou": 0.9,
                },
            )

            self.assertFalse(result.ok)
            self.assertLess(result.data["views"][0]["silhouette_iou"], 0.9)
            self.assertEqual(["front"], result.data["failed_views"])


    def test_headless_export_requires_existing_blend_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch(
                "ordax_dev_agent.blender_actions.find_blender",
                return_value=Path("/fake/blender"),
            ):
                result = registry.execute(
                    "blender.export_headless",
                    {
                        "project": "hordax",
                        "blend_file": "missing.blend",
                        "output_path": "Artifacts/test.glb",
                        "format": "glb",
                    },
                )

            self.assertFalse(result.ok)
            self.assertIn("existing .blend", result.summary)

    def test_local_watchdog_is_windows_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            config = self.make_config(Path(raw))
            with patch("ordax_dev_agent.main.sys.platform", "linux"):
                process = _start_local_watchdog(config)

            self.assertIsNone(process)


    def test_material_apply_normalizes_and_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_material_apply",
                    {
                        "object_name": "Acrylic",
                        "material_name": "Crystal",
                        "base_color": [0.82, 0.94, 1.0, 0.18],
                        "roughness": 0.08,
                        "transmission": 1.0,
                        "alpha": 0.18,
                        "ior": 1.49,
                        "surface_render_method": "BLENDED",
                        "transparency_overlap": True,
                    },
                )

        self.assertTrue(result.ok)
        self.assertEqual("material_apply", result.data["operation"])
        self.assertEqual("Crystal", result.data["payload"]["material_name"])
        self.assertEqual(1.0, result.data["payload"]["transmission"])
        self.assertEqual(0.18, result.data["payload"]["alpha"])
        self.assertEqual("BLENDED", result.data["payload"]["surface_render_method"])
        self.assertTrue(result.data["payload"]["transparency_overlap"])

    def test_material_apply_rejects_invalid_surface_render_method(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.execute(
                    "blender.live_material_apply",
                    {
                        "object_name": "Acrylic",
                        "material_name": "Crystal",
                        "surface_render_method": "NOISY",
                    },
                )

        self.assertFalse(result.ok)
        self.assertIn("DITHERED or BLENDED", result.summary)
        live.assert_not_called()

    def test_material_apply_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.execute(
                    "blender.live_material_apply",
                    {
                        "object_name": "Acrylic",
                        "material_name": "Crystal",
                        "python": "arbitrary",
                    },
                )

        self.assertFalse(result.ok)
        self.assertIn("unsupported field(s): python", result.summary)
        live.assert_not_called()

    def test_upload_result_artifacts_accepts_multiview_artifact_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "front.png"
            path.write_bytes(b"png")
            uploaded_paths = []

            class FakeControl:
                def upload_artifact(self, job, artifact_path, *, kind, metadata):
                    uploaded_paths.append((artifact_path, kind, metadata))
                    return {"path": str(artifact_path), "kind": kind}

            job = SimpleNamespace(action="blender.live_multiview_capture")
            result = ActionResult(
                True,
                "captured",
                {"artifacts": [{"view": "front", "artifact": str(path)}]},
            )

            uploaded = _upload_result_artifacts(FakeControl(), job, result)

        self.assertEqual(1, len(uploaded))
        self.assertEqual(path, uploaded_paths[0][0])


    def test_live_import_asset_accepts_single_obj_under_home(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.home()) as raw:
            root = Path(raw)
            project = root / "hordax"
            project.mkdir()
            asset_dir = root / "assets"
            asset_dir.mkdir()
            source = asset_dir / "couple.obj"
            source.write_text("o couple\n", encoding="utf-8")
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_import_asset",
                    {
                        "source_path": str(asset_dir),
                        "object_name": "Biblical_Couple",
                    },
                )

        self.assertTrue(result.ok)
        self.assertEqual("import_asset", result.data["operation"])
        self.assertEqual(str(source.resolve()), result.data["payload"]["source_path"])
        self.assertEqual("Biblical_Couple", result.data["payload"]["object_name"])

    def test_live_import_asset_refuses_source_outside_home(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            source = root / "asset.obj"
            source.write_text("o x\n", encoding="utf-8")
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.execute(
                    "blender.live_import_asset",
                    {"source_path": str(source)},
                )

        if source.resolve().is_relative_to(Path.home().resolve()):
            self.skipTest("temporary directory is inside home on this runner")
        self.assertFalse(result.ok)
        self.assertIn("home directory", result.summary)
        live.assert_not_called()



    def test_live_animate_transform_normalizes_and_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.execute(
                    "blender.live_animate_transform",
                    {
                        "object_name": "Acrylic",
                        "keyframes": [
                            {"frame": 1, "location": [0, 0, 0.05]},
                            {"frame": 48, "location": [0, 0, 0.15]},
                            {"frame": 96, "location": [0, 0, 0.05]},
                        ],
                        "interpolation": "bezier",
                        "fps": 24,
                    },
                )

        self.assertTrue(result.ok)
        self.assertEqual("animate_transform", result.data["operation"])
        self.assertEqual("BEZIER", result.data["payload"]["interpolation"])
        self.assertEqual(3, len(result.data["payload"]["keyframes"]))
        self.assertEqual(24, result.data["payload"]["fps"])

    def test_live_animate_transform_rejects_unsorted_frames(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.execute(
                    "blender.live_animate_transform",
                    {
                        "object_name": "Acrylic",
                        "keyframes": [
                            {"frame": 20, "location": [0, 0, 0.15]},
                            {"frame": 10, "location": [0, 0, 0.05]},
                        ],
                    },
                )

        self.assertFalse(result.ok)
        self.assertIn("strictly increasing", result.summary)
        live.assert_not_called()



    def test_live_batch_executes_validated_steps_locally(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            calls = []

            def fake_transform(payload):
                calls.append(("object_transform", payload))
                return ActionResult(
                    True,
                    "moved",
                    {"object": {"name": payload["object_name"]}},
                )

            def fake_material(payload):
                calls.append(("material_apply", payload))
                return ActionResult(
                    True,
                    "material",
                    {"object": {"name": payload["object_name"]}},
                )

            with patch.object(
                registry,
                "blender_live_object_transform",
                side_effect=fake_transform,
            ), patch.object(
                registry,
                "blender_live_material_apply",
                side_effect=fake_material,
            ):
                result = registry.blender_live_batch(
                    {
                        "steps": [
                            {
                                "op": "object_transform",
                                "payload": {
                                    "object_name": "Part",
                                    "location": [1, 2, 3],
                                },
                            },
                            {
                                "op": "material_apply",
                                "payload": {
                                    "object_name": "Part",
                                    "material_name": "Mat",
                                },
                            },
                        ]
                    }
                )

        self.assertTrue(result.ok, f"{result.summary}: {result.data}")
        self.assertEqual(2, result.data["completed_steps"])
        self.assertEqual(
            ["object_transform", "material_apply"],
            [item[0] for item in calls],
        )

    def test_live_batch_rejects_unlisted_operations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.blender_live_batch(
                {
                    "steps": [
                        {"op": "run_script", "payload": {}},
                    ]
                }
            )

        self.assertFalse(result.ok)
        self.assertIn("not allowed", result.summary)

    def test_viewport_proxy_dispatches_non_destructive_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.blender_live_viewport_proxy(
                    {
                        "object_name": "HighPoly",
                        "target_faces": 120000,
                    }
                )

        self.assertTrue(result.ok)
        self.assertEqual("viewport_proxy", result.data["operation"])
        self.assertEqual(120000, result.data["payload"]["target_faces"])
        self.assertTrue(result.data["payload"]["enabled"])



    def test_live_create_camera_normalizes_and_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.blender_live_create_camera(
                    {
                        "name": "Product_Camera",
                        "location": [0.0, -0.2, 0.08],
                        "target": [0.0, 0.0, 0.04],
                        "lens_mm": 55,
                    }
                )

        self.assertTrue(result.ok)
        self.assertEqual("create_camera", result.data["operation"])
        self.assertEqual("Product_Camera", result.data["payload"]["name"])
        self.assertEqual(55.0, result.data["payload"]["lens_mm"])

    def test_live_create_light_rejects_unknown_type(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.blender_live_create_light(
                    {
                        "name": "Bad",
                        "light_type": "LASER",
                        "location": [0, 0, 1],
                    }
                )

        self.assertFalse(result.ok)
        self.assertIn("AREA, POINT, SUN, or SPOT", result.summary)
        live.assert_not_called()

    def test_live_scene_presentation_dispatches_closed_world_settings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.blender_live_scene_presentation(
                    {
                        "render_engine": "BLENDER_EEVEE",
                        "resolution_x": 1200,
                        "resolution_y": 1200,
                        "world_strength": 0.2,
                    }
                )

        self.assertTrue(result.ok)
        self.assertEqual("scene_presentation", result.data["operation"])
        self.assertEqual(1200, result.data["payload"]["resolution_x"])
        self.assertEqual(0.2, result.data["payload"]["world_strength"])



    def test_bake_work_proxy_dispatches_closed_world_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            fake_live = SimpleNamespace(
                request=lambda operation, payload, timeout_seconds: SimpleNamespace(
                    ok=True,
                    summary="accepted",
                    data={
                        "operation": operation,
                        "payload": payload,
                        "timeout_seconds": timeout_seconds,
                    },
                )
            )
            with patch.object(registry, "_blender_live", return_value=fake_live):
                result = registry.blender_live_bake_work_proxy(
                    {
                        "object_name": "HighPoly",
                        "proxy_name": "HighPoly_Work",
                        "target_faces": 90000,
                        "remove_source": True,
                    }
                )

        self.assertTrue(result.ok)
        self.assertEqual("bake_work_proxy", result.data["operation"])
        self.assertEqual("HighPoly_Work", result.data["payload"]["proxy_name"])
        self.assertEqual(90000, result.data["payload"]["target_faces"])
        self.assertTrue(result.data["payload"]["remove_source"])

    def test_bake_work_proxy_rejects_invalid_proxy_name(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            with patch.object(registry, "_blender_live") as live:
                result = registry.blender_live_bake_work_proxy(
                    {
                        "object_name": "HighPoly",
                        "proxy_name": "../bad",
                    }
                )

        self.assertFalse(result.ok)
        self.assertIn("unsupported characters", result.summary)
        live.assert_not_called()



if __name__ == "__main__":
    unittest.main()
