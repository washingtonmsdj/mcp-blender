import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_studio.web_desktop import StudioApi


class OrdaxStudioWebTests(unittest.TestCase):
    def test_web_shell_api_reuses_persistent_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (project / "index.html").write_text("<h1>demo</h1>", encoding="utf-8")
            (project / "src").mkdir()
            (project / "src" / "demo.py").write_text("value = 1\n", encoding="utf-8")
            (root / "agent-settings.json").write_text(json.dumps({
                "default_project": "demo",
                "projects": {"demo": {"path": str(project), "apps": []}},
            }), encoding="utf-8")
            env = {
                "ORDAX_AGENT_STATE_DIR": str(root),
                "ORDAX_MEMORY_DB": str(root / "memory.db"),
            }
            with patch.dict(os.environ, env, clear=False):
                api = StudioApi()
                boot = api.bootstrap()
                self.assertEqual("demo", boot["project"]["slug"])
                self.assertIsNotNone(boot["session_id"])
                self.assertEqual("web", boot["preview"]["data"]["mode"])

                inventory = api.inventory()
                self.assertTrue(inventory["ok"])
                self.assertIn("src/demo.py", [item["path"] for item in inventory["data"]["entries"]])

                opened = api.read_file("src/demo.py")
                self.assertTrue(opened["ok"])
                saved = api.save_file("src/demo.py", "value = 2\n", opened["data"]["sha256"])
                self.assertTrue(saved["ok"])
                self.assertEqual("value = 2\n", (project / "src" / "demo.py").read_text(encoding="utf-8"))

    def test_project_catalog_exposes_git_repository_identity(self):
        if not shutil.which("git"):
            self.skipTest("git is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "repo"
            project.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(project)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(project), "remote", "add", "origin", "https://github.com/example/demo.git"], check=True)
            (root / "agent-settings.json").write_text(json.dumps({
                "default_project": "demo",
                "projects": {
                    "demo": {"path": str(project), "apps": []},
                    "demo-alias": {"path": str(project), "apps": []},
                },
            }), encoding="utf-8")
            env = {"ORDAX_AGENT_STATE_DIR": str(root), "ORDAX_MEMORY_DB": str(root / "memory.db")}
            with patch.dict(os.environ, env, clear=False):
                catalog = StudioApi().projects_catalog()
            self.assertEqual(1, len(catalog["projects"]))
            repo = catalog["projects"][0]["repository"]
            self.assertTrue(repo["is_repository"])
            self.assertEqual("main", repo["branch"])
            self.assertEqual("https://github.com/example/demo.git", repo["remote"])

    def test_web_shell_contains_repository_first_home_and_preview_workspace(self):
        html = Path(__file__).resolve().parents[1] / "ordax_studio" / "studio.html"
        content = html.read_text(encoding="utf-8")
        self.assertIn('id="projectHome"', content)
        self.assertIn('id="projectGrid"', content)
        self.assertIn('id="workspace"', content)
        self.assertIn('id="webPreview"', content)
        self.assertIn("projects_catalog", content)
        self.assertIn("openProject", content)
        self.assertIn("preview_start", content)
        self.assertIn("preview_capture", content)


if __name__ == "__main__":
    unittest.main()
