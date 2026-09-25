import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class GameAssetUnitySemanticActionsTests(unittest.TestCase):
    def make_config(self, root: Path) -> AgentConfig:
        project = root / "project"
        asset = project / "Assets" / "OrdaX" / "Generated" / "hero.fbx"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"fake-fbx")
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
                "game": {
                    "path": str(project),
                    "apps": ["blender", "unity"],
                    "allowed_branches": [],
                }
            },
            default_project="game",
        )

    def evidence(self, **updates):
        data = {
            "modelImporterPresent": True,
            "modelAnimationType": "Human",
            "modelImportAnimation": True,
            "modelMeshCount": 2,
            "modelAnimationClipCount": 3,
            "modelBoneCount": 64,
            "modelBlendShapeCount": 8,
            "modelLodGroupCount": 1,
        }
        data.update(updates)
        return data

    def test_registry_exposes_unity_semantic_audit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            status = registry.execute("agent.status", {})
            self.assertTrue(status.ok)
            self.assertIn("game_assets.unity_semantic_audit", status.data["actions"])

    def test_humanoid_character_requirements_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            with patch.object(
                registry,
                "game_assets_unity_model_audit",
                return_value=ActionResult(
                    True,
                    "Unity model import audit passed",
                    {
                        "asset_path": "Assets/OrdaX/Generated/hero.fbx",
                        "engine": "unity",
                        "audit": self.evidence(),
                    },
                ),
            ):
                result = registry.execute(
                    "game_assets.unity_semantic_audit",
                    {
                        "project": "game",
                        "asset_path": "Assets/OrdaX/Generated/hero.fbx",
                        "expected_animation_type": "humanoid",
                        "require_animation_import": True,
                        "min_meshes": 1,
                        "min_bones": 50,
                        "min_animation_clips": 1,
                        "min_blend_shapes": 1,
                        "min_lod_groups": 1,
                        "max_lod_groups": 1,
                    },
                )

            self.assertTrue(result.ok, result.summary)
            self.assertTrue(result.data["engine_loaded"])
            self.assertTrue(result.data["semantic_requirements_passed"])
            self.assertEqual([], result.data["failures"])
            self.assertIn("avatar_mapping_not_yet_reported_by_companion", result.data["limitations"])

    def test_loaded_asset_can_fail_semantic_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            with patch.object(
                registry,
                "game_assets_unity_model_audit",
                return_value=ActionResult(
                    True,
                    "Unity model import audit passed",
                    {
                        "asset_path": "Assets/OrdaX/Generated/hero.fbx",
                        "engine": "unity",
                        "audit": self.evidence(
                            modelAnimationType="Generic",
                            modelAnimationClipCount=0,
                            modelLodGroupCount=0,
                        ),
                    },
                ),
            ):
                result = registry.execute(
                    "game_assets.unity_semantic_audit",
                    {
                        "project": "game",
                        "asset_path": "Assets/OrdaX/Generated/hero.fbx",
                        "expected_animation_type": "human",
                        "min_animation_clips": 1,
                        "min_lod_groups": 1,
                    },
                )

            self.assertFalse(result.ok)
            self.assertTrue(result.data["engine_loaded"])
            self.assertFalse(result.data["semantic_requirements_passed"])
            self.assertEqual(3, len(result.data["failures"]))

    def test_old_companion_is_retryable_not_false_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            with patch.object(
                registry,
                "game_assets_unity_model_audit",
                return_value=ActionResult(
                    True,
                    "Unity model import audit passed",
                    {
                        "asset_path": "Assets/OrdaX/Generated/hero.fbx",
                        "engine": "unity",
                        "audit": {"modelImporterPresent": True},
                    },
                ),
            ):
                result = registry.execute(
                    "game_assets.unity_semantic_audit",
                    {"project": "game", "asset_path": "Assets/OrdaX/Generated/hero.fbx"},
                )

            self.assertFalse(result.ok)
            self.assertTrue(result.data["retryable"])
            self.assertIn("modelBoneCount", result.data["missing_fields"])

    def test_invalid_requirement_is_rejected_before_unity_call(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            with patch.object(registry, "game_assets_unity_model_audit") as audit:
                result = registry.execute(
                    "game_assets.unity_semantic_audit",
                    {
                        "project": "game",
                        "asset_path": "Assets/OrdaX/Generated/hero.fbx",
                        "min_lod_groups": 3,
                        "max_lod_groups": 1,
                    },
                )
            self.assertFalse(result.ok)
            self.assertIn("min_lod_groups cannot exceed", result.summary)
            audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
