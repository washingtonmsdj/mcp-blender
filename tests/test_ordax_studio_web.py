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
                briefing = api.briefing()
                self.assertTrue(briefing["ok"])
                self.assertIn("continuity", briefing["data"])
                search = api.search("value")
                self.assertTrue(search["ok"])
                self.assertIn("src/demo.py", [item["path"] for item in search["data"]["matches"]])
                task = api.task_add("Refinar a experiência do preview")
                self.assertTrue(task["ok"])
                updated = api.briefing()
                self.assertEqual(
                    "Refinar a experiência do preview",
                    updated["data"]["continuity"]["open_tasks"][-1]["title"],
                )

    def test_package_without_dev_script_is_not_misclassified_as_web_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (project / "package.json").write_text(
                json.dumps({"scripts": {"test": "echo ok"}}), encoding="utf-8"
            )
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
            self.assertEqual("artifact", boot["preview"]["data"]["mode"])

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
        root = Path(__file__).resolve().parents[1] / "ordax_studio"
        html = (root / "studio.html").read_text(encoding="utf-8")
        script = (root / "assets" / "studio.js").read_text(encoding="utf-8")
        stylesheet = (root / "assets" / "studio.css").read_text(encoding="utf-8")
        self.assertIn('id="projectHome"', html)
        self.assertIn('id="projectGrid"', html)
        self.assertIn('id="workspace"', html)
        self.assertIn('id="workspaceProjectList"', html)
        self.assertIn('id="webPreview"', html)
        self.assertIn('class="projectSidebar"', html)
        self.assertIn('class="mainPane"', html)
        self.assertIn('class="previewPane"', html)
        self.assertIn('data-view="agent"', html)
        self.assertIn('data-view="mcp"', html)
        self.assertIn("projects_catalog", script)
        self.assertIn("openProject", script)
        self.assertIn("prepareProjectPreview", script)
        self.assertIn("preview_start", script)
        self.assertIn("preview_capture", script)
        self.assertIn("workspaceProjectList", stylesheet)
        self.assertIn("previewFocus", stylesheet)


if __name__ == "__main__":
    unittest.main()
