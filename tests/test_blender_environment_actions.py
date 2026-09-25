import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class BlenderEnvironmentActionTests(unittest.TestCase):
    def make_config(self, root: Path) -> AgentConfig:
        project = root / "project"
        project.mkdir(parents=True, exist_ok=True)
        return AgentConfig(
            agent_name="test-agent",
            supabase_url=None,
            publishable_key=None,
            poll_seconds=1.0,
            state_dir=root / "state",
            agent_repo_path=root / "agent",
            hordax_path=project,
            bridge_path=root / "bridge",
            projects={
                "salvador": {
                    "path": str(project),
                    "apps": ["blender", "unity"],
                    "allowed_branches": [],
                }
            },
            default_project="salvador",
        )

    def test_registry_exposes_blender_environment_apply(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            status = registry.execute("agent.status", {})
            self.assertTrue(status.ok)
            self.assertIn("blender.environment_apply", status.data["actions"])

    def test_environment_apply_materializes_output_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            project = root / "project"
            source = project / "salvador.blend"
            source.write_bytes(b"BLENDER")
            registry = ActionRegistry(config)

            def fake_run(command, *, cwd=None, timeout=0, env=None):
                output = Path(command[command.index("--output") + 1])
                report = Path(command[command.index("--report") + 1])
                manifest = Path(command[command.index("--environment") + 1])
                environment = json.loads(manifest.read_text(encoding="utf-8"))
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"BLENDER-ENV")
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(
                    json.dumps(
                        {
                            "ok": True,
                            "schema": "ordax.blender-visual-environment/1",
                            "environment_schema": environment["schema"],
                            "environment_name": environment["name"],
                            "ocean": {"enabled": environment["ocean"]["enabled"]},
                        }
                    ),
                    encoding="utf-8",
                )
                return ActionResult(True, "command completed", {"command": command})

            with patch(
                "ordax_dev_agent.blender_environment_actions.find_blender",
                return_value=Path("C:/Blender/blender.exe"),
            ), patch(
                "ordax_dev_agent.blender_environment_actions._run",
                side_effect=fake_run,
            ):
                result = registry.execute(
                    "blender.environment_apply",
                    {
                        "project": "salvador",
                        "blend_file": "salvador.blend",
                        "output_path": "render/salvador-environment.blend",
                        "environment": {
                            "preset": "salvador_golden_hour",
                            "ocean": {"foam_amount": 0.25},
                        },
                    },
                )

            self.assertTrue(result.ok, result.summary)
            self.assertEqual("ordax.visual-environment/1", result.data["environment"]["schema"])
            self.assertEqual(0.25, result.data["environment"]["ocean"]["foam_amount"])
            self.assertTrue((project / "render" / "salvador-environment.blend").is_file())
            self.assertTrue((project / "render" / "salvador-environment.environment.json").is_file())

    def test_refuses_overwrite_without_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            project = root / "project"
            (project / "salvador.blend").write_bytes(b"BLENDER")
            target = project / "render" / "salvador-environment.blend"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"EXISTING")
            registry = ActionRegistry(config)
            with patch(
                "ordax_dev_agent.blender_environment_actions.find_blender",
                return_value=Path("C:/Blender/blender.exe"),
            ):
                result = registry.execute(
                    "blender.environment_apply",
                    {
                        "project": "salvador",
                        "blend_file": "salvador.blend",
                        "output_path": "render/salvador-environment.blend",
                    },
                )
            self.assertFalse(result.ok)
            self.assertIn("overwrite=true", result.summary)


if __name__ == "__main__":
    unittest.main()
