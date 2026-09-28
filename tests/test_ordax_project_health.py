import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class OrdaxProjectHealthTests(unittest.TestCase):
    def test_health_reports_outdated_blender_companion_without_mutation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            project = root / "project"
            project.mkdir()
            (project / ".git").mkdir()
            config = AgentConfig(
                agent_name="test", poll_seconds=1, state_dir=root / "state",
                agent_repo_path=root / "agent", hordax_path=root / "hordax",
                bridge_path=root / "bridge",
                projects={"demo": {"path": str(project), "apps": ["blender"]}},
                default_project="demo",
            )
            env = {"ORDAX_MEMORY_DB": str(root / "memory.db")}
            with patch.dict(os.environ, env, clear=False):
                registry = ActionRegistry(config)
                blender = ActionResult(False, "Visible Blender live session is not running", {
                    "presence_fresh": False,
                    "protocol_version": 9,
                    "protocol_compatible": True,
                    "companion_current": False,
                    "presence": {
                        "blender_version": "5.2.2",
                        "file": str(project / "scene.blend"),
                    },
                })
                git = ActionResult(True, "command completed", {"stdout": " M scene.blend\n"})
                with patch.object(registry, "blender_live_status", return_value=blender), \
                     patch.object(registry, "git_status", return_value=git):
                    result = registry.execute("agent.project_health", {"project": "demo"})

            self.assertTrue(result.ok)
            self.assertEqual("attention", result.data["state"])
            self.assertEqual("update_required", result.data["adapters"]["blender"]["state"])
            self.assertEqual("5.2.2", result.data["adapters"]["blender"]["blender_version"])
            self.assertTrue(result.data["git"]["dirty"])
            self.assertEqual(1, result.data["git"]["changed_entries"])
            self.assertEqual("disabled", result.data["adapters"]["unity"]["state"])


if __name__ == "__main__":
    unittest.main()
