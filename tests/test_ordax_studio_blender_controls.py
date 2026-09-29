from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.models import ActionResult
from ordax_studio.web_desktop import StudioApi


class OrdaxStudioBlenderControlTests(unittest.TestCase):
    def _api(self, directory: str) -> StudioApi:
        root = Path(directory)
        project = root / "project"
        project.mkdir()
        (root / "agent-settings.json").write_text(
            json.dumps({
                "default_project": "demo",
                "projects": {
                    "demo": {
                        "path": str(project),
                        "apps": ["blender"],
                        "blender": {},
                    }
                },
            }),
            encoding="utf-8",
        )
        env = {
            "ORDAX_AGENT_STATE_DIR": str(root),
            "ORDAX_MEMORY_DB": str(root / "memory.db"),
        }
        with patch.dict(os.environ, env, clear=False):
            return StudioApi()

    def test_prepare_exposes_actionable_restart_state(self):
        with tempfile.TemporaryDirectory() as directory:
            api = self._api(directory)
            with patch.object(api.agent, "execute") as execute:
                execute.side_effect = [
                    ActionResult(False, "not connected", {}),
                    ActionResult(False, "no match", {"no_match": True}),
                    ActionResult(True, "instances", {"unmanaged_blender_pids": [7001]}),
                ]
                result = api.blender_prepare()

        self.assertTrue(result["ok"])
        self.assertEqual("restart_required", result["data"]["state"])
        self.assertTrue(result["data"]["bridge_installable"])
        self.assertTrue(result["data"]["requires_restart"])
        self.assertFalse(result["data"]["can_start"])
        self.assertFalse(result["data"]["can_capture"])

    def test_prepare_exposes_idle_state_when_no_blender_is_running(self):
        with tempfile.TemporaryDirectory() as directory:
            api = self._api(directory)
            with patch.object(api.agent, "execute") as execute:
                execute.side_effect = [
                    ActionResult(False, "not connected", {}),
                    ActionResult(False, "no match", {"no_match": True}),
                    ActionResult(True, "instances", {"unmanaged_blender_pids": []}),
                ]
                result = api.blender_prepare()

        self.assertEqual("idle", result["data"]["state"])
        self.assertTrue(result["data"]["can_start"])
        self.assertFalse(result["data"]["requires_restart"])

    def test_install_bridge_rechecks_connection_state(self):
        with tempfile.TemporaryDirectory() as directory:
            api = self._api(directory)
            with patch.object(api.agent, "execute") as execute:
                execute.side_effect = [
                    ActionResult(True, "installed", {"installed": ["bridge"]}),
                    ActionResult(False, "not connected", {}),
                    ActionResult(False, "no match", {"no_match": True}),
                    ActionResult(True, "instances", {"unmanaged_blender_pids": [7010]}),
                ]
                result = api.blender_install_bridge()

        self.assertTrue(result["ok"])
        self.assertEqual(["bridge"], result["data"]["installation"]["installed"])
        self.assertEqual("restart_required", result["data"]["connection"]["state"])
        self.assertEqual(
            ["blender.adoption_install", "blender.live_status", "blender.adopt", "blender.instances"],
            [call.args[0] for call in execute.call_args_list],
        )

    def test_explicit_adopt_returns_capture_ready_state(self):
        with tempfile.TemporaryDirectory() as directory:
            api = self._api(directory)
            with patch.object(api.agent, "execute") as execute:
                execute.return_value = ActionResult(
                    True,
                    "adopted",
                    {"presence": {"pid": 8123, "file": "scene.blend"}},
                )
                result = api.blender_adopt(8123)

        self.assertEqual("adopted", result["data"]["state"])
        self.assertEqual(8123, result["data"]["pid"])
        self.assertTrue(result["data"]["can_capture"])
        self.assertFalse(result["data"]["can_start"])
        self.assertEqual(8123, execute.call_args.args[1]["pid"])

    def test_explicit_adopt_rejects_invalid_pid_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            api = self._api(directory)
            with patch.object(api.agent, "execute") as execute:
                result = api.blender_adopt(0)

        self.assertFalse(result["ok"])
        execute.assert_not_called()

    def test_start_returns_connected_state_after_live_status(self):
        with tempfile.TemporaryDirectory() as directory:
            api = self._api(directory)
            with patch.object(api.agent, "execute") as execute:
                execute.side_effect = [
                    ActionResult(True, "started", {"pid": 9001}),
                    ActionResult(
                        True,
                        "ready",
                        {"presence": {"pid": 9001, "file": "scene.blend"}},
                    ),
                ]
                result = api.blender_start()

        self.assertEqual("connected", result["data"]["state"])
        self.assertEqual(9001, result["data"]["pid"])
        self.assertTrue(result["data"]["can_capture"])
        self.assertEqual(
            ["blender.live_start", "blender.live_status"],
            [call.args[0] for call in execute.call_args_list],
        )


if __name__ == "__main__":
    unittest.main()
