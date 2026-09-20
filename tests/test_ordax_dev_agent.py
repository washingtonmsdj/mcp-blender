import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from PIL import Image, ImageDraw

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.main import _start_local_watchdog
from ordax_dev_agent.config import AgentConfig


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
            self.assertIn("unity.compile", result.data["actions"])
            self.assertIn("blender.run_python", result.data["actions"])
            self.assertIn("blender.live_start", result.data["actions"])
            self.assertIn("blender.live_status", result.data["actions"])
            self.assertIn("blender.live_inspect", result.data["actions"])
            self.assertIn("blender.live_scene_snapshot", result.data["actions"])
            self.assertIn("blender.live_scene_reset", result.data["actions"])
            self.assertIn("blender.live_object_inspect", result.data["actions"])
            self.assertIn("blender.live_object_fingerprints", result.data["actions"])
            self.assertIn("blender.live_contact_audit", result.data["actions"])
            self.assertIn("blender.live_quality_gate", result.data["actions"])
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
            self.assertNotIn("shell.exec", result.data["actions"])


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
                "ordax_dev_agent.actions.find_blender",
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


if __name__ == "__main__":
    unittest.main()
