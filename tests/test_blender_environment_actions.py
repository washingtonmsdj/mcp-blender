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

    def test_schema_exposes_blender_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            result = registry.execute("visual.environment_schema", {})
            self.assertTrue(result.ok)
            self.assertIn("blender", result.data["materialization"])
            self.assertEqual(
                "visual.environment_write",
                result.data["materialization"]["blender"]["action"],
            )

    def test_environment_write_materializes_output_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            project = root / "project"
            (project / "salvador.blend").write_bytes(b"BLENDER")
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
                    "visual.environment_write",
                    {
                        "project": "salvador",
                        "output_path": "render/environment.json",
                        "environment": {
                            "preset": "salvador_golden_hour",
                            "ocean": {"foam_amount": 0.25},
                        },
                        "blender": {
                            "blend_file": "salvador.blend",
                            "output_path": "render/salvador-environment.blend",
                        },
                    },
                )

            self.assertTrue(result.ok, result.summary)
            self.assertEqual("ordax.visual-environment/1", result.data["environment"]["schema"])
            self.assertEqual(0.25, result.data["environment"]["ocean"]["foam_amount"])
            self.assertIn("blender", result.data)
            self.assertTrue((project / "render" / "environment.json").is_file())
            self.assertTrue((project / "render" / "salvador-environment.blend").is_file())
            self.assertTrue((project / "render" / "salvador-environment.environment.json").is_file())

    def test_refuses_unknown_nested_blender_field(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute(
                "visual.environment_write",
                {
                    "project": "salvador",
                    "output_path": "environment.json",
                    "blender": {"shell": "dangerous"},
                },
            )
            self.assertFalse(result.ok)
            self.assertIn("unsupported blender field", result.summary)


if __name__ == "__main__":
    unittest.main()
