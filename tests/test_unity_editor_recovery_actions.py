import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class UnityEditorRecoveryActionTests(unittest.TestCase):
    def make_registry(self, root: Path) -> tuple[ActionRegistry, Path]:
        project = root / "project"
        (project / "Assets").mkdir(parents=True)
        (project / "ProjectSettings").mkdir()
        (project / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.6.1f1\n",
            encoding="utf-8",
        )
        config = AgentConfig(
            "test",
            None,
            None,
            5,
            root / "state",
            root / "agent",
            root / "hordax",
            root / "bridge",
            projects={"salvador": {"path": str(project), "apps": ["unity"]}},
            default_project="salvador",
        )
        return ActionRegistry(config), project

    def test_stuck_editor_termination_requires_single_exact_editor_process(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry, project = self.make_registry(root)
            (project / "Temp").mkdir()
            (project / "Temp" / "UnityLockfile").write_text("lock", encoding="utf-8")
            editor = root / "Unity" / "6000.6.1f1" / "Editor" / "Unity.exe"
            editor.parent.mkdir(parents=True)
            editor.write_bytes(b"test")

            active = {"state": "active", "path": str(project / "Temp" / "UnityLockfile")}
            stale = {"state": "stale", "path": str(project / "Temp" / "UnityLockfile")}
            missing = {"state": "missing", "path": str(project / "Temp" / "UnityLockfile")}
            stopped = subprocess.CompletedProcess(
                args=["powershell.exe"],
                returncode=0,
                stdout="",
                stderr="",
            )

            with patch("ordax_dev_agent.unity_actions.sys.platform", "win32"), patch(
                "ordax_dev_agent.unity_actions.find_unity",
                return_value=editor,
            ), patch(
                "ordax_dev_agent.unity_actions._windows_unity_lock_probe",
                side_effect=[active, stale, missing],
            ), patch(
                "ordax_dev_agent.unity_actions._windows_unity_processes",
                return_value=[
                    {"pid": 16860, "path": str(editor), "title": "project - Unity"}
                ],
            ), patch(
                "ordax_dev_agent.unity_actions.subprocess.run",
                return_value=stopped,
            ):
                result = registry.execute(
                    "unity.editor_terminate_stuck",
                    {"wait_seconds": 5},
                )

            self.assertTrue(result.ok, f"{result.summary}: {result.data}")
            self.assertEqual(16860, result.data["pid"])
            self.assertTrue(result.data["stale_lock_cleared"])
            self.assertEqual("missing", result.data["project_lock_probe"]["state"])

    def test_stuck_editor_termination_fails_closed_for_ambiguous_processes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry, project = self.make_registry(root)
            (project / "Temp").mkdir()
            (project / "Temp" / "UnityLockfile").write_text("lock", encoding="utf-8")
            editor = root / "Unity" / "6000.6.1f1" / "Editor" / "Unity.exe"
            editor.parent.mkdir(parents=True)
            editor.write_bytes(b"test")
            active = {"state": "active", "path": str(project / "Temp" / "UnityLockfile")}

            with patch("ordax_dev_agent.unity_actions.sys.platform", "win32"), patch(
                "ordax_dev_agent.unity_actions.find_unity",
                return_value=editor,
            ), patch(
                "ordax_dev_agent.unity_actions._windows_unity_lock_probe",
                return_value=active,
            ), patch(
                "ordax_dev_agent.unity_actions._windows_unity_processes",
                return_value=[
                    {"pid": 1, "path": str(editor), "title": "A"},
                    {"pid": 2, "path": str(editor), "title": "B"},
                ],
            ), patch(
                "ordax_dev_agent.unity_actions.subprocess.run"
            ) as stop:
                result = registry.execute("unity.editor_terminate_stuck", {})

            self.assertFalse(result.ok)
            self.assertIn("exactly one", result.summary)
            stop.assert_not_called()

    def test_hub_install_editor_is_typed_and_verifies_installation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry, _project = self.make_registry(root)
            hub = root / "Unity Hub.exe"
            hub.write_bytes(b"test")
            completed = subprocess.CompletedProcess(
                args=[str(hub)],
                returncode=0,
                stdout="installed",
                stderr="",
            )

            with patch("ordax_dev_agent.unity_actions.sys.platform", "win32"), patch(
                "ordax_dev_agent.unity_actions._hub_editor_install_exists",
                side_effect=[False, True],
            ), patch(
                "ordax_dev_agent.unity_actions._find_unity_hub",
                return_value=hub,
            ), patch(
                "ordax_dev_agent.unity_actions.subprocess.run",
                return_value=completed,
            ) as run:
                result = registry.execute(
                    "unity.hub_install_editor",
                    {
                        "version": "6000.6.2f1",
                        "changeset": "770e33f6875c",
                        "timeout_seconds": 120,
                    },
                )

            self.assertTrue(result.ok)
            command = run.call_args.args[0]
            self.assertIn("--headless", command)
            self.assertIn("6000.6.2f1", command)
            self.assertIn("770e33f6875c", command)
            self.assertFalse(run.call_args.kwargs["shell"])


    def test_editor_start_can_target_exact_hub_version(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry, _project = self.make_registry(root)
            editor_path = root / "Unity" / "6000.6.2f1" / "Editor" / "Unity.exe"
            editor_path.parent.mkdir(parents=True)
            editor_path.write_bytes(b"test")

            bridge = Mock()
            bridge.presence_is_fresh.side_effect = [False, True]
            bridge.project_appears_open.return_value = False
            bridge.status.return_value = {
                "presence_fresh": False,
                "presence": {"protocol": "ordax-generic-v5"},
            }

            with patch.object(registry, "_editor", return_value=bridge), patch(
                "ordax_dev_agent.unity_actions._find_hub_editor_executable",
                return_value=editor_path,
            ), patch(
                "ordax_dev_agent.unity_actions.find_unity"
            ) as legacy_find, patch(
                "ordax_dev_agent.unity_actions.subprocess.Popen",
                return_value=SimpleNamespace(pid=4242),
            ) as popen:
                result = registry.execute(
                    "unity.editor_start",
                    {"version": "6000.6.2f1", "wait_seconds": 1},
                )

            self.assertTrue(result.ok, f"{result.summary}: {result.data}")
            legacy_find.assert_not_called()
            self.assertEqual(str(editor_path), popen.call_args.args[0][0])
            self.assertEqual("6000.6.2f1", result.data["requested_version"])

    def test_recover_resume_runs_closed_loop_on_same_release_stream(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry, _project = self.make_registry(root)
            ok = ActionResult(True, "ok", {})
            started = ActionResult(
                True,
                "started",
                {"presence": {"unityVersion": "6000.6.2f1", "protocol": "ordax-generic-v5"}},
            )

            with patch(
                "ordax_dev_agent.unity_actions.unity_project_profile",
                side_effect=[
                    {"unity_version": "6000.6.1f1"},
                    {"unity_version": "6000.6.2f1"},
                ],
            ), patch.object(
                registry, "unity_editor_terminate_stuck", return_value=ok
            ) as terminate, patch.object(
                registry, "unity_hub_install_editor", return_value=ok
            ) as install, patch.object(
                registry, "unity_install_companion", return_value=ok
            ) as companion, patch.object(
                registry, "unity_editor_start", return_value=started
            ) as start, patch.object(
                registry, "unity_compile", return_value=ok
            ) as compile_, patch.object(
                registry, "unity_scene_summary", return_value=ok
            ) as summary, patch.object(
                registry, "unity_physics_audit", return_value=ok
            ) as physics, patch.object(
                registry, "unity_spatial_audit", return_value=ok
            ) as spatial, patch.object(
                registry, "unity_play_start", return_value=ok
            ) as play, patch.object(
                registry,
                "unity_capture",
                return_value=ActionResult(
                    True,
                    "captured",
                    {"artifact": "capture.png", "snapshot_path": "capture.json"},
                ),
            ) as capture:
                result = registry.execute(
                    "unity.recover_resume",
                    {
                        "version": "6000.6.2f1",
                        "changeset": "770e33f6875c",
                    },
                )

            self.assertTrue(result.ok, f"{result.summary}: {result.data}")
            terminate.assert_called_once()
            install.assert_called_once()
            companion.assert_called_once()
            start.assert_called_once()
            self.assertEqual(
                "6000.6.2f1",
                start.call_args.args[0]["version"],
            )
            compile_.assert_called_once()
            summary.assert_called_once()
            physics.assert_called_once()
            spatial.assert_called_once()
            play.assert_called_once()
            capture.assert_called_once()
            self.assertEqual("capture.png", result.data["artifact"])
            self.assertEqual(
                [
                    "terminate_stuck_editor",
                    "install_target_editor",
                    "install_companion",
                    "start_target_editor",
                    "compile",
                    "scene_summary",
                    "play_start",
                    "physics_audit",
                    "spatial_audit",
                    "capture",
                ],
                [item["step"] for item in result.data["steps"]],
            )

    def test_recover_resume_refuses_cross_stream_editor(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry, _project = self.make_registry(root)

            result = registry.execute(
                "unity.recover_resume",
                {"version": "6000.5.10f1"},
            )

            self.assertFalse(result.ok)
            self.assertIn("current Unity release stream", result.summary)
            self.assertEqual("6000.6.1f1", result.data["current_version"])
            self.assertEqual("6000.5.10f1", result.data["target_version"])


if __name__ == "__main__":
    unittest.main()
