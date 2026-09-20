import tempfile
import tomllib
import unittest
from pathlib import Path

from mcp_blender_unity import __version__ as bridge_package_version
from ordax_dev_agent import __version__ as dev_agent_version
from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.blender_live_bridge import (
    BUNDLE_FORMAT_VERSION,
    EXPECTED_PROTOCOL_VERSION,
)
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.references import MANIFEST_VERSION
from ordax_dev_agent.versioning import component_versions


class ComponentVersioningTests(unittest.TestCase):
    def make_config(self, root: Path) -> AgentConfig:
        return AgentConfig(
            agent_name="version-test",
            supabase_url=None,
            publishable_key=None,
            poll_seconds=5.0,
            state_dir=root / "state",
            agent_repo_path=root / "agent",
            hordax_path=root / "hordax",
            bridge_path=root / "bridge",
        )

    def test_distribution_metadata_matches_bridge_package_version(self) -> None:
        root = Path(__file__).resolve().parents[1]
        metadata = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            bridge_package_version,
            metadata["project"]["version"],
        )

    def test_component_versions_are_independent_and_explicit(self) -> None:
        versions = component_versions()
        self.assertEqual(bridge_package_version, versions["bridge_package"])
        self.assertEqual(dev_agent_version, versions["dev_agent"])
        self.assertEqual(
            EXPECTED_PROTOCOL_VERSION,
            versions["blender_live_protocol"],
        )
        self.assertEqual(
            BUNDLE_FORMAT_VERSION,
            versions["blender_companion_bundle_format"],
        )
        self.assertEqual(
            MANIFEST_VERSION,
            versions["reference_contract"],
        )
        self.assertNotEqual(
            versions["bridge_package"],
            versions["dev_agent"],
        )

    def test_agent_status_exposes_component_versions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "hordax").mkdir()
            registry = ActionRegistry(self.make_config(root))
            result = registry.execute("agent.status", {})

        self.assertTrue(result.ok)
        self.assertEqual(component_versions(), result.data["versions"])


if __name__ == "__main__":
    unittest.main()
