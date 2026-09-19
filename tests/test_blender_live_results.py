import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
