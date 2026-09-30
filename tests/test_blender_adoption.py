from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from types import SimpleNamespace

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.blender_adoption import BlenderAdoptionManager
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.projects import Project


class BlenderAdoptionTests(unittest.TestCase):
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
        self.blend = self.project_root / "scene.blend"
        self.blend.write_bytes(b"BLENDER")
        self.project = Project(
            "demo",
            self.project_root,
            ("blender",),
            blender={"scripts_dir": "automation/blender"},
        )
        self.config = SimpleNamespace(state_dir=self.state)
        self.appdata = self.root / "roaming"
        (self.appdata / "Blender Foundation" / "Blender" / "5.2").mkdir(parents=True)
        self.manager = BlenderAdoptionManager(
            self.config,
            {"demo": self.project},
            assets_root=self.assets,
            companion_fingerprint="fingerprint-1",
            appdata=self.appdata,
            enable_addon=False,
        )

    def tearDown(self):
        self.temp.cleanup()

    def _discovery(
        self,
        pid: int,
        *,
        age: float = 0.0,
        file: Path | str | None = None,
        dirty: bool = False,
        attached_project: str | None = None,
    ):
        path = self.state / "blender-discovery" / f"{pid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw_file = str(self.blend if file is None else file)
        path.write_text(
            json.dumps({
                "pid": pid,
                "addon_fingerprint": self.manager.addon_fingerprint,
                "timestamp": time.time() - age,
                "file": raw_file,
                "is_dirty": dirty,
                "blender_version": "5.2.2",
                "attached_project": attached_project,
            }),
            encoding="utf-8",
        )
        return path

    def test_install_writes_config_and_version_startup_script(self):
        result = self.manager.install()
        self.assertTrue(result.ok, result.summary)
        target = self.appdata / "Blender Foundation" / "Blender" / "5.2" / "scripts" / "addons" / "ordax_studio_bridge" / "__init__.py"
        self.assertTrue(target.is_file())
        config = json.loads(self.manager.config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["version"], 1)
        self.assertEqual(config["projects"]["demo"]["root"], str(self.project_root.resolve()))
        self.assertEqual(config["companion_fingerprint"], "fingerprint-1")

    def test_enable_timeout_is_recovered_when_probe_confirms_addon_enabled(self):
        self.manager.enable_addon = True
        timeout = subprocess.TimeoutExpired(cmd=["blender"], timeout=60)
        probe = SimpleNamespace(
            returncode=0,
            stdout="ORDAX_STUDIO_ADDON_PRESENT=True\n",
        )
        with patch(
            "ordax_dev_agent.blender_adoption.find_blender",
            return_value=Path("C:/Blender/blender.exe"),
        ), patch(
            "ordax_dev_agent.blender_adoption.subprocess.run",
            side_effect=[timeout, probe],
        ) as run:
            result = self.manager._enable_installed_addon()
        self.assertTrue(result["enabled"])
        self.assertTrue(result["enable_timed_out"])
        self.assertEqual(2, run.call_count)

    def test_instances_ignore_stale_and_match_project_root(self):
        self._discovery(101)
        self._discovery(102, age=20)
        outside = self.root / "outside.blend"
        outside.write_bytes(b"OUTSIDE")
        self._discovery(103, file=outside)
        instances = self.manager.instances()
        self.assertEqual({item["pid"] for item in instances}, {101, 103})
        matches = self.manager.matching_instances(self.project)
        self.assertEqual([item["pid"] for item in matches], [101])

    def test_system_blender_pids_parses_windows_tasklist(self):
        completed = SimpleNamespace(
            returncode=0,
            stdout='"blender.exe","1234","Console","1","500,000 K"\n"blender.exe","5678","Console","1","600,000 K"\n',
        )
        with patch("ordax_dev_agent.blender_adoption.os.name", "nt"), patch(
            "ordax_dev_agent.blender_adoption.subprocess.run", return_value=completed
        ):
            self.assertEqual(self.manager.system_blender_pids(), [1234, 5678])

    def test_multiple_matching_instances_require_explicit_pid(self):
        self._discovery(201)
        self._discovery(202)
        result = self.manager.request_adoption(self.project, wait_seconds=0.5)
        self.assertFalse(result.ok)
        self.assertTrue(result.data["ambiguous"])
        self.assertEqual({item["pid"] for item in result.data["instances"]}, {201, 202})

    def test_request_adoption_waits_for_matching_presence_pid(self):
        pid = 301
        self._discovery(pid)

        def companion_reply():
            request = self.state / "blender-adoption" / f"{pid}.json"
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and not request.is_file():
                time.sleep(0.01)
            presence = self.state / "blender-live" / "demo" / "presence.json"
            presence.parent.mkdir(parents=True, exist_ok=True)
            presence.write_text(
                json.dumps({
                    "pid": pid,
                    "project": "demo",
                    "companion_fingerprint": "fingerprint-1",
                }),
                encoding="utf-8",
            )

        thread = threading.Thread(target=companion_reply, daemon=True)
        thread.start()
        result = self.manager.request_adoption(self.project, pid=pid, wait_seconds=2.0)
        thread.join(timeout=2.0)
        self.assertTrue(result.ok, result.summary)
        self.assertEqual(result.data["pid"], pid)
        self.assertEqual(result.data["presence"]["project"], "demo")

    def _reply_to_adoption(self, pid: int, project: str = "demo") -> threading.Thread:
        def companion_reply():
            request = self.state / "blender-adoption" / f"{pid}.json"
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and not request.is_file():
                time.sleep(0.01)
            presence = self.state / "blender-live" / project / "presence.json"
            presence.parent.mkdir(parents=True, exist_ok=True)
            presence.write_text(
                json.dumps({
                    "pid": pid,
                    "project": project,
                    "companion_fingerprint": "fingerprint-1",
                }),
                encoding="utf-8",
            )

        thread = threading.Thread(target=companion_reply, daemon=True)
        thread.start()
        return thread

    def test_outdated_loaded_addon_requires_restart_before_adoption(self):
        path = self._discovery(400, file="")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["addon_fingerprint"] = "old-addon"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = self.manager.request_adoption(
            self.project,
            pid=400,
            wait_seconds=0.5,
            allow_blank=True,
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.data["restart_required"])
        self.assertEqual(result.data["install_action"], "blender.adoption_install")

    def test_blank_window_requires_explicit_opt_in(self):
        self._discovery(401, file="")
        result = self.manager.request_adoption(self.project, pid=401, wait_seconds=0.5)
        self.assertFalse(result.ok)
        self.assertTrue(result.data["requires_allow_blank"])

    def test_clean_blank_window_can_be_adopted_by_explicit_pid(self):
        pid = 402
        self._discovery(pid, file="")
        thread = self._reply_to_adoption(pid)
        result = self.manager.request_adoption(
            self.project,
            pid=pid,
            wait_seconds=2.0,
            allow_blank=True,
        )
        thread.join(timeout=2.0)
        self.assertTrue(result.ok, result.summary)
        request = json.loads((self.state / "blender-adoption" / f"{pid}.json").read_text(encoding="utf-8"))
        self.assertTrue(request["allow_blank"])

    def test_dirty_blank_window_cannot_be_adopted(self):
        self._discovery(403, file="", dirty=True)
        result = self.manager.request_adoption(
            self.project,
            pid=403,
            wait_seconds=0.5,
            allow_blank=True,
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.data["dirty"])

    def test_explicit_pid_cannot_adopt_file_from_another_project(self):
        outside = self.root / "outside.blend"
        outside.write_bytes(b"OUTSIDE")
        self._discovery(404, file=outside)
        result = self.manager.request_adoption(
            self.project,
            pid=404,
            wait_seconds=0.5,
            allow_blank=True,
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.data["project_mismatch"])

    def test_blender_addon_asset_is_valid_python(self):
        source = Path(__file__).resolve().parents[1] / "ordax_dev_agent" / "assets" / "ordax_studio_blender_addon.py"
        compile(source.read_text(encoding="utf-8-sig"), str(source), "exec")


class BlenderStartAdoptionTests(unittest.TestCase):
    def make_registry(self, root: Path) -> ActionRegistry:
        project = root / "project"
        project.mkdir(parents=True)
        config = AgentConfig(
            agent_name="adoption-test",
            poll_seconds=1.0,
            state_dir=root / "state",
            agent_repo_path=root / "managed",
            hordax_path=root / "hordax",
            bridge_path=root / "bridge",
            projects={"demo": {"path": str(project), "apps": ["blender"], "blender": {}}},
            default_project="demo",
        )
        return ActionRegistry(config)

    def _run_start(self, adoption: ActionResult):
        raw = tempfile.TemporaryDirectory()
        self.addCleanup(raw.cleanup)
        registry = self.make_registry(Path(raw.name))
        manager = Mock()
        manager.request_adoption.return_value = adoption
        manager.instances.return_value = []
        manager.system_blender_pids.return_value = []
        with patch("ordax_dev_agent.blender_actions.BlenderLiveBridge") as bridge_class:
            live = bridge_class.return_value
            live.presence_is_fresh.return_value = False
            live.status.return_value = {"presence_fresh": True, "presence": {"pid": 42}}
            live.start.return_value = ActionResult(True, "spawned", {"pid": 99})
            with patch.object(registry, "_blender_adoption_manager", return_value=manager):
                result = registry.execute("blender.live_start", {"project": "demo", "wait_seconds": 1})
        return result, live

    def test_live_start_does_not_spawn_after_successful_adoption(self):
        result, live = self._run_start(ActionResult(True, "adopted", {"pid": 42}))
        self.assertTrue(result.ok)
        self.assertIn("adopted", result.summary.lower())
        live.start.assert_not_called()

    def test_live_start_does_not_spawn_when_adoption_is_ambiguous(self):
        result, live = self._run_start(ActionResult(False, "ambiguous", {"ambiguous": True}))
        self.assertFalse(result.ok)
        live.start.assert_not_called()

    def test_live_start_spawns_only_when_no_candidate_matches(self):
        result, live = self._run_start(ActionResult(False, "no match", {"no_match": True}))
        self.assertTrue(result.ok)
        self.assertEqual(result.summary, "spawned")
        live.start.assert_called_once()

    def test_live_start_offers_clean_blank_window_instead_of_spawning(self):
        raw = tempfile.TemporaryDirectory()
        self.addCleanup(raw.cleanup)
        registry = self.make_registry(Path(raw.name))
        manager = Mock()
        manager.request_adoption.return_value = ActionResult(False, "no match", {"no_match": True})
        manager.instances.return_value = [{
            "pid": 4321,
            "file": "",
            "is_dirty": False,
            "attached_project": None,
        }]
        manager.system_blender_pids.return_value = [4321]
        with patch("ordax_dev_agent.blender_actions.BlenderLiveBridge") as bridge_class:
            live = bridge_class.return_value
            live.presence_is_fresh.return_value = False
            with patch.object(registry, "_blender_adoption_manager", return_value=manager):
                result = registry.execute("blender.live_start", {"project": "demo", "wait_seconds": 1})
        self.assertFalse(result.ok)
        self.assertEqual(result.data["blank_adoptable_pids"], [4321])
        live.start.assert_not_called()

    def test_live_start_refuses_second_window_when_unmanaged_blender_exists(self):
        raw = tempfile.TemporaryDirectory()
        self.addCleanup(raw.cleanup)
        registry = self.make_registry(Path(raw.name))
        manager = Mock()
        manager.request_adoption.return_value = ActionResult(False, "no match", {"no_match": True})
        manager.instances.return_value = []
        manager.system_blender_pids.return_value = [4321]
        with patch("ordax_dev_agent.blender_actions.BlenderLiveBridge") as bridge_class:
            live = bridge_class.return_value
            live.presence_is_fresh.return_value = False
            with patch.object(registry, "_blender_adoption_manager", return_value=manager):
                result = registry.execute("blender.live_start", {"project": "demo", "wait_seconds": 1})
        self.assertFalse(result.ok)
        self.assertTrue(result.data["unmanaged_blender_running"])
        self.assertEqual(result.data["blender_pids"], [4321])
        live.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
