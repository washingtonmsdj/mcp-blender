import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ordax_dev_agent.blender_live_bridge import BlenderLiveBridge
from ordax_dev_agent.projects import Project


class BlenderLiveResultTests(unittest.TestCase):
    def make_bridge(self, root: Path) -> BlenderLiveBridge:
        project_root = root / "project"
        (project_root / "automation" / "blender").mkdir(parents=True)
        project = Project(
            slug="demo",
            root=project_root,
            apps=("blender",),
            blender={"scripts_dir": "automation/blender"},
        )
        config = SimpleNamespace(state_dir=root / "state")
        return BlenderLiveBridge(config, project)

    def test_result_survives_without_live_presence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            bridge._ensure_dirs()
            command_id = uuid.uuid4().hex
            (bridge.results / f"{command_id}.json").write_text(
                json.dumps(
                    {
                        "id": command_id,
                        "ok": True,
                        "summary": "done",
                        "value": 42,
                    }
                ),
                encoding="utf-8",
            )

            result = bridge.result(command_id)

            self.assertTrue(result.ok)
            self.assertEqual("done", result.summary)
            self.assertTrue(result.data["durable_result"])
            self.assertEqual(42, result.data["value"])

    def test_missing_result_is_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            result = bridge.result(uuid.uuid4().hex)

            self.assertFalse(result.ok)
            self.assertTrue(result.data["retryable"])

    def test_noncanonical_command_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            result = bridge.result(str(uuid.uuid4()))

            self.assertFalse(result.ok)
            self.assertIn("canonical", result.summary)

    def test_missing_result_reports_inflight_command(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            bridge._ensure_dirs()
            command_id = uuid.uuid4().hex
            (bridge.inflight / f"{command_id}.json").write_text(
                json.dumps({"id": command_id, "operation": "run_script"}),
                encoding="utf-8",
            )

            result = bridge.result(command_id)

            self.assertFalse(result.ok)
            self.assertTrue(result.data["retryable"])
            self.assertTrue(result.data["in_progress"])

    def test_status_lists_inflight_commands(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            bridge._ensure_dirs()
            command_id = uuid.uuid4().hex
            (bridge.inflight / f"{command_id}.json").write_text("{}", encoding="utf-8")

            status = bridge.status()

            self.assertIn(command_id, status["inflight_commands"])
            self.assertEqual(str(bridge.inflight), status["inflight_root"])


    def test_outdated_companion_allows_advertised_maintenance_operation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            bridge._ensure_dirs()
            command_id = "a" * 32
            (bridge.responses / f"{command_id}.json").write_text(
                json.dumps({"id": command_id, "ok": True, "summary": "saved"}),
                encoding="utf-8",
            )
            outdated = {
                "protocol_compatible": False,
                "companion_current": False,
                "capabilities": ["save", "quit"],
            }
            with (
                patch.object(bridge, "presence_is_fresh", return_value=True),
                patch.object(bridge, "status", return_value=outdated),
                patch("ordax_dev_agent.blender_live_bridge.uuid.uuid4", return_value=SimpleNamespace(hex=command_id)),
            ):
                result = bridge.request("save", {"target_path": "demo.blend"}, timeout_seconds=1)

            self.assertTrue(result.ok)
            self.assertEqual("saved", result.summary)

    def test_outdated_companion_blocks_nonmaintenance_operation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bridge = self.make_bridge(Path(raw))
            outdated = {
                "protocol_compatible": False,
                "companion_current": False,
                "capabilities": ["run_script"],
            }
            with (
                patch.object(bridge, "presence_is_fresh", return_value=True),
                patch.object(bridge, "status", return_value=outdated),
            ):
                result = bridge.request("run_script", {"script_path": "demo.py"})

            self.assertFalse(result.ok)
            self.assertIn("protocol is outdated", result.summary)

    def test_companion_uses_shared_transform_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        companion = (
            root / "ordax_dev_agent" / "assets" / "blender_live_companion.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            '"blender_modeling_contracts.py"',
            companion,
        )
        self.assertIn(
            "_normalize_transform_request = "
            "_MODELING_CONTRACTS.normalize_transform_request",
            companion,
        )
        self.assertIn(
            'transport_fields={"id", "operation"}',
            companion,
        )
        self.assertNotIn("def _coerce_vector(", companion)

    def test_validated_modeling_mutations_are_advertised_and_use_normal_dispatch(self) -> None:
        root = Path(__file__).resolve().parents[1]
        companion = (
            root / "ordax_dev_agent" / "assets" / "blender_live_companion.py"
        ).read_text(encoding="utf-8")
        benchmark = (root / "scripts" / "blender_benchmark.py").read_text(
            encoding="utf-8"
        )

        start = companion.index("CAPABILITIES = [")
        end = companion.index("_LAST_PRESENCE_AT", start)
        capabilities = companion[start:end]
        self.assertIn('"create_primitive"', capabilities)
        self.assertIn('"add_modifier"', capabilities)
        self.assertNotIn("__smoke_create_primitive", companion)
        self.assertNotIn("__smoke_add_modifier", companion)
        self.assertNotIn("smoke_only_unregistered", companion)

        self.assertIn("def _modeling_create_primitive(", companion)
        self.assertIn("def _modeling_add_modifier(", companion)
        self.assertIn('operation == "create_primitive"', companion)
        self.assertIn('operation == "add_modifier"', companion)
        self.assertIn('"operation": "create_primitive"', companion)
        self.assertIn('"operation": "add_modifier"', companion)

        self.assertIn('"smoke-model-create.json"', benchmark)
        self.assertIn('"smoke-model-modifier.json"', benchmark)
        self.assertIn('"smoke-model-create-duplicate.json"', benchmark)
        self.assertIn('"smoke-model-modifier-duplicate.json"', benchmark)


if __name__ == "__main__":
    unittest.main()
