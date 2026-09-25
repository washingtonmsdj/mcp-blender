import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.visual_environment import ENVIRONMENT_SCHEMA


class BlenderVisualEnvironmentActionTests(unittest.TestCase):
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
                    "blender": {"blend_file": "salvador.blend"},
                }
            },
            default_project="salvador",
        )

    def test_registry_exposes_blender_environment_actions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            status = registry.execute("agent.status", {})
            self.assertTrue(status.ok)
            self.assertIn("visual.blender_environment_build", status.data["actions"])
            self.assertIn("visual.blender_environment_audit", status.data["actions"])

    def test_build_creates_derivative_and_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            source = root / "project" / "salvador.blend"
            source.write_bytes(b"canonical-source-blend")
            before = source.read_bytes()

            def fake_run(command, *, cwd=None, timeout_seconds=0, **_kwargs):
                self.assertEqual(root / "project", Path(cwd))
                self.assertEqual(420, timeout_seconds)
                self.assertIn("--disable-autoexec", command)
                self.assertIn(str(source), command)
                request = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
                self.assertEqual("apply", request["operation"])
                self.assertEqual(ENVIRONMENT_SCHEMA, request["environment"]["schema"])
                self.assertEqual("Salvador Golden Hour", request["environment"]["name"])
                output = Path(request["output_path"])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"derived-environment-blend")
                Path(request["report_path"]).write_text(
                    json.dumps(
                        {
                            "ok": True,
                            "schema": "ordax.blender-environment-build/1",
                            "audit": {
                                "environment_metadata_valid": True,
                                "world": {"sky_nodes": ["Sky Texture"]},
                                "sun": {"present": True, "light_type": "SUN"},
                                "ocean": {"modifier_present": True},
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

            registry = ActionRegistry(config)
            with patch(
                "ordax_dev_agent.visual_environment_actions.find_blender",
                return_value=Path("C:/Blender/blender.exe"),
            ), patch(
                "ordax_dev_agent.visual_environment_actions.run_process",
                side_effect=fake_run,
            ):
                result = registry.execute(
                    "visual.blender_environment_build",
                    {
                        "project": "salvador",
                        "blend_file": "salvador.blend",
                        "environment": {"preset": "salvador_golden_hour"},
                        "output_path": "derived/salvador-golden.blend",
                        "timeout_seconds": 420,
                    },
                )

            self.assertTrue(result.ok, result.summary)
            self.assertEqual(before, source.read_bytes())
            self.assertTrue(result.data["source_preserved"])
            self.assertTrue((root / "project" / "derived" / "salvador-golden.blend").is_file())
            self.assertEqual(
                "ordax.blender-environment-build/1",
                result.data["report"]["schema"],
            )

    def test_audit_is_readonly_and_returns_blender_proof(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            source = root / "project" / "salvador.blend"
            source.write_bytes(b"environment-derivative")
            before = source.read_bytes()

            def fake_run(command, *, cwd=None, timeout_seconds=0, **_kwargs):
                request = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
                self.assertEqual("audit", request["operation"])
                self.assertNotIn("output_path", request)
                self.assertNotIn("environment", request)
                Path(request["report_path"]).write_text(
                    json.dumps(
                        {
                            "ok": True,
                            "schema": "ordax.blender-environment-audit/1",
                            "audit": {
                                "environment_metadata_valid": True,
                                "world": {"sky_nodes": ["Sky Texture"]},
                                "sun": {"present": True, "light_type": "SUN"},
                                "ocean": {"modifier_present": True},
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

            registry = ActionRegistry(config)
            with patch(
                "ordax_dev_agent.visual_environment_actions.find_blender",
                return_value=Path("C:/Blender/blender.exe"),
            ), patch(
                "ordax_dev_agent.visual_environment_actions.run_process",
                side_effect=fake_run,
            ):
                result = registry.execute(
                    "visual.blender_environment_audit",
                    {"project": "salvador", "blend_file": "salvador.blend"},
                )

            self.assertTrue(result.ok, result.summary)
            self.assertEqual(before, source.read_bytes())
            self.assertTrue(result.data["source_preserved"])
            self.assertEqual("ordax.blender-environment-audit/1", result.data["report"]["schema"])

    def test_build_refuses_to_overwrite_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.make_config(root)
            (root / "project" / "salvador.blend").write_bytes(b"source")
            registry = ActionRegistry(config)
            result = registry.execute(
                "visual.blender_environment_build",
                {
                    "project": "salvador",
                    "blend_file": "salvador.blend",
                    "output_path": "salvador.blend",
                },
            )
            self.assertFalse(result.ok)
            self.assertIn("must differ", result.summary)


if __name__ == "__main__":
    unittest.main()
