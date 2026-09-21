import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


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

            self.assertTrue(result.ok)
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


if __name__ == "__main__":
    unittest.main()
