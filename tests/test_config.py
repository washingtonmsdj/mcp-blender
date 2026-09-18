import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_blender_unity.config import (
    find_unity,
    read_unity_api_compatibility_level,
    read_unity_project_version,
    unity_installation_diagnostics,
)


class ConfigTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "Project"
        (project / "Assets").mkdir(parents=True)
        settings = project / "ProjectSettings"
        settings.mkdir()
        (settings / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.6.1f1\n", encoding="utf-8"
        )
        (settings / "ProjectSettings.asset").write_text(
            "  apiCompatibilityLevel: 6\n", encoding="utf-8"
        )
        return project

    def test_reads_project_version_and_api_level(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            project = self.make_project(Path(raw_root))
            self.assertEqual(read_unity_project_version(project), "6000.6.1f1")
            self.assertEqual(read_unity_api_compatibility_level(project), 6)

    def test_finds_required_editor_in_configured_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            project = self.make_project(root)
            unity = root / "Editors" / "6000.6.1f1" / "Editor" / "Unity.exe"
            unity.parent.mkdir(parents=True)
            unity.write_bytes(b"test")
            with patch.dict(os.environ, {"UNITY_EDITOR_ROOTS": str(root / "Editors")}, clear=False):
                self.assertEqual(find_unity(project), unity)

    def test_reports_missing_reference_assemblies(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            project = self.make_project(root)
            unity = root / "Editor" / "Unity.exe"
            unity.parent.mkdir(parents=True)
            unity.write_bytes(b"test")
            diagnostics = unity_installation_diagnostics(unity, project)
            self.assertTrue(diagnostics["reference_assemblies_required"])
            self.assertFalse(diagnostics["reference_assemblies_available"])
            self.assertFalse(diagnostics["installation_healthy"])


if __name__ == "__main__":
    unittest.main()
