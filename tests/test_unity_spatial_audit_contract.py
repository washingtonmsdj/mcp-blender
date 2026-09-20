import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class UnitySpatialAuditContractTests(unittest.TestCase):
    def test_generic_companion_reports_world_transform_and_camera_evidence(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "ordax_dev_agent"
            / "assets"
            / "OrdaXGenericAgent.cs"
        ).read_text(encoding="utf-8")

        for expected in (
            'case "spatial_audit": SpatialAudit(reply); break;',
            "mirroredTransformCount",
            "nearZeroScaleCount",
            "extremeScaleCount",
            "extremePositionCount",
            "nonFiniteTransformCount",
            "invertedRootCount",
            "cameraInsideColliderCount",
            "cameraBelowRenderBounds",
            "renderBoundsCenter",
            "renderBoundsSize",
            "cameraPosition",
            "cameraEulerAngles",
            "rotation = t.eulerAngles",
        ):
            self.assertIn(expected, source)

        self.assertIn("renderer.bounds", source)
        self.assertIn("collider.bounds.Contains(camera.transform.position)", source)
        self.assertIn("Vector3.Dot(transform.up, Vector3.up)", source)

    def test_registry_routes_spatial_audit_to_live_unity_companion(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            project = root / "project"
            project.mkdir()
            config = AgentConfig(
                "test",
                None,
                None,
                5,
                root / "state",
                root / "agent",
                root / "hordax",
                root / "bridge",
                projects={"world": {"path": str(project), "apps": ["unity"]}},
                default_project="world",
            )
            registry = ActionRegistry(config)
            editor = Mock()
            editor.project_appears_open.return_value = True
            editor.presence_is_fresh.return_value = True
            editor.request.return_value = ActionResult(
                True,
                "Spatial audit completed with warnings",
                {"mirroredTransformCount": 2},
            )

            with patch.object(registry, "_editor", return_value=editor):
                result = registry.execute("unity.spatial_audit", {})

            self.assertTrue(result.ok)
            self.assertEqual(2, result.data["mirroredTransformCount"])
            self.assertEqual("spatial_audit", editor.request.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
