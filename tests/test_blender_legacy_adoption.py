from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ordax_dev_agent.blender_adoption import BlenderAdoptionManager
from ordax_dev_agent.projects import Project


class LegacyBlendMCPAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.assets = self.root / "assets"
        self.assets.mkdir()
        (self.assets / "blender_live_companion.py").write_text("# companion\n", encoding="utf-8")
        (self.assets / "ordax_studio_blender_addon.py").write_text("# addon\n", encoding="utf-8")
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        (self.project_root / "automation" / "blender").mkdir(parents=True)
        self.project = Project(
            "demo",
            self.project_root,
            ("blender",),
            blender={
                "scripts_dir": "automation/blender",
                "legacy_blendmcp_port": 9877,
            },
        )
        self.manager = BlenderAdoptionManager(
            SimpleNamespace(state_dir=self.state),
            {"demo": self.project},
            assets_root=self.assets,
            companion_fingerprint="fp-1",
            appdata=self.root / "roaming",
            enable_addon=False,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_bridge_migration_registers_ordax_and_waits_for_same_pid(self):
        pid = 4321
        calls: list[dict] = []

        def rpc(port, payload, timeout_seconds=5.0):
            self.assertEqual(port, 9877)
            calls.append(payload)
            if payload["type"] == "get_addon_version":
                return {"status": "success", "result": {"version": "1.30.0"}}
            self.assertEqual(payload["type"], "execute_code")
            self.assertIn("ordax_studio_bridge.register()", payload["params"]["code"])
            return {"status": "success", "result": {"executed": True, "result": "ORDAX_ADOPTION_REGISTERED\n"}}

        def publish_presence():
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and len(calls) < 2:
                time.sleep(0.01)
            path = self.state / "blender-live" / "demo" / "presence.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({
                    "pid": pid,
                    "project": "demo",
                    "companion_fingerprint": "fp-1",
                    "file": str(self.project_root / "scene.blend"),
                }),
                encoding="utf-8",
            )

        thread = threading.Thread(target=publish_presence, daemon=True)
        thread.start()
        with patch.object(self.manager, "system_blender_pids", return_value=[pid]), patch.object(
            self.manager,
            "_legacy_bridge_rpc",
            side_effect=rpc,
        ):
            result = self.manager.request_adoption(self.project, wait_seconds=2.0)
        thread.join(timeout=2.0)

        self.assertTrue(result.ok, result.summary)
        self.assertEqual(result.data["pid"], pid)
        self.assertTrue(result.data["legacy_bridge_migration"])
        self.assertEqual([item["type"] for item in calls], ["get_addon_version", "execute_code"])

    def test_legacy_bridge_requires_explicit_pid_when_multiple_blenders_are_running(self):
        with patch.object(self.manager, "system_blender_pids", return_value=[1001, 1002]):
            result = self.manager.request_adoption(self.project, wait_seconds=0.5)
        self.assertFalse(result.ok)
        self.assertTrue(result.data["ambiguous"])
        self.assertEqual(result.data["blender_pids"], [1001, 1002])

    def test_invalid_legacy_bridge_port_fails_closed(self):
        project = Project(
            "demo",
            self.project_root,
            ("blender",),
            blender={"scripts_dir": "automation/blender", "legacy_blendmcp_port": 80},
        )
        manager = BlenderAdoptionManager(
            SimpleNamespace(state_dir=self.state),
            {"demo": project},
            assets_root=self.assets,
            companion_fingerprint="fp-1",
            appdata=self.root / "roaming",
            enable_addon=False,
        )
        result = manager.request_adoption(project, wait_seconds=0.5)
        self.assertFalse(result.ok)
        self.assertIn("legacy_blendmcp_port", result.summary)


if __name__ == "__main__":
    unittest.main()
