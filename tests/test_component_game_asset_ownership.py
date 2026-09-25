import unittest

from ordax_dev_agent.component_updates import plan_component_update


class GameAssetComponentOwnershipTests(unittest.TestCase):
    def test_generated_asset_pipeline_has_no_unknown_runtime_paths(self) -> None:
        plan = plan_component_update(
            [
                "ordax_dev_agent/game_asset_image_actions.py",
                "ordax_dev_agent/game_asset_artifact_actions.py",
                "ordax_dev_agent/game_asset_status_actions.py",
                "ordax_dev_agent/generated_asset_actions.py",
                "ordax_dev_agent/assets/blender_generated_asset_ingest.py",
            ]
        )
        self.assertEqual(plan["affected_components"], ["adapter-game-assets"])
        self.assertEqual(plan["unknown_paths"], [])
        self.assertTrue(plan["device_agent_restart_required"])


if __name__ == "__main__":
    unittest.main()
