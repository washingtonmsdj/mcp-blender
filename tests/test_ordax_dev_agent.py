import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


class AgentActionRegistryTests(unittest.TestCase):
    def make_config(self, root: Path) -> AgentConfig:
        return AgentConfig(
            agent_name="test-agent",
            supabase_url=None,
            publishable_key=None,
            poll_seconds=5.0,
            state_dir=root / "state",
            agent_repo_path=root / "agent",
            hordax_path=root / "hordax",
            bridge_path=root / "bridge",
        )

    def test_unknown_action_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            result = registry.execute("shell.exec", {"command": "whoami"})
            self.assertFalse(result.ok)
            self.assertIn("not allowed", result.summary)

    def test_status_lists_only_registered_actions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            result = registry.execute("agent.status", {})
            self.assertTrue(result.ok)
            self.assertIn("agent.update", result.data["actions"])
            self.assertIn("unity.compile", result.data["actions"])
            self.assertIn("blender.run_python", result.data["actions"])
            self.assertIn("blender.live_start", result.data["actions"])
            self.assertIn("blender.live_status", result.data["actions"])
            self.assertIn("blender.live_inspect", result.data["actions"])
            self.assertIn("blender.live_scene_snapshot", result.data["actions"])
            self.assertIn("blender.live_scene_reset", result.data["actions"])
            self.assertIn("blender.live_object_inspect", result.data["actions"])
            self.assertIn("blender.live_contact_audit", result.data["actions"])
            self.assertIn("blender.live_object_transform", result.data["actions"])
            self.assertIn("blender.live_object_metadata", result.data["actions"])
            self.assertIn("blender.live_checkpoint_create", result.data["actions"])
            self.assertIn("blender.live_checkpoint_list", result.data["actions"])
            self.assertIn("blender.live_checkpoint_restore", result.data["actions"])
            self.assertIn("blender.live_trajectory", result.data["actions"])
            self.assertIn("blender.live_generation_pass", result.data["actions"])
            self.assertIn("blender.live_result", result.data["actions"])
            self.assertIn("blender.live_run_script", result.data["actions"])
            self.assertIn("blender.live_capture", result.data["actions"])
            self.assertIn("blender.live_save", result.data["actions"])
            self.assertIn("blender.live_stop", result.data["actions"])
            self.assertIn("blender.asset_search", result.data["actions"])
            self.assertIn("blender.asset_manifest", result.data["actions"])
            self.assertNotIn("shell.exec", result.data["actions"])


if __name__ == "__main__":
    unittest.main()
