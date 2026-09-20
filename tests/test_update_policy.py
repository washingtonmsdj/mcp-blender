import unittest

from ordax_dev_agent.update_policy import (
    install_contract,
    install_contract_changed,
)


BASE = """
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mcp-blender-unity"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "mcp>=1.0.0,<2.0.0",
  "supabase>=2.18.0,<3.0.0",
]

[project.scripts]
ordax-dev-agent = "ordax_dev_agent.main:main"

[tool.setuptools.packages.find]
include = ["mcp_blender_unity*", "ordax_dev_agent*"]

[tool.setuptools.package-data]
ordax_dev_agent = ["assets/*.py", "assets/*.cs"]
"""


class AgentUpdatePolicyTests(unittest.TestCase):
    def test_version_and_package_data_do_not_force_reinstall(self) -> None:
        changed = BASE.replace('version = "0.1.0"', 'version = "0.3.0"').replace(
            '["assets/*.py", "assets/*.cs"]',
            '["assets/*.py", "assets/*.cs", "assets/*.json"]',
        )
        self.assertFalse(install_contract_changed(BASE, changed))

    def test_dependency_change_requires_reinstall(self) -> None:
        changed = BASE.replace(
            '"supabase>=2.18.0,<3.0.0",',
            '"supabase>=2.18.0,<3.0.0",\n  "Pillow>=10,<12",',
        )
        self.assertTrue(install_contract_changed(BASE, changed))

    def test_entry_point_change_requires_reinstall(self) -> None:
        changed = BASE.replace(
            'ordax-dev-agent = "ordax_dev_agent.main:main"',
            'ordax-dev-agent = "ordax_dev_agent.bootstrap:main"',
        )
        self.assertTrue(install_contract_changed(BASE, changed))

    def test_build_backend_change_requires_reinstall(self) -> None:
        changed = BASE.replace(
            'build-backend = "setuptools.build_meta"',
            'build-backend = "other.backend"',
        )
        self.assertTrue(install_contract_changed(BASE, changed))

    def test_invalid_toml_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid pyproject"):
            install_contract("[project")


if __name__ == "__main__":
    unittest.main()
