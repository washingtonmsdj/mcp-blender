import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.models import ActionResult
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

    def test_blender_bootstrap_exposes_typed_modeling_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (root / "agent-settings.json").write_text(json.dumps({
                "default_project": "demo",
                "projects": {"demo": {"path": str(project), "apps": ["blender"], "blender": {}}},
            }), encoding="utf-8")
            env = {
                "ORDAX_AGENT_STATE_DIR": str(root),
                "ORDAX_MEMORY_DB": str(root / "memory.db"),
            }
            with patch.dict(os.environ, env, clear=False):
                boot = StudioApi().bootstrap()

        modeling = boot["modeling"]
        self.assertTrue(modeling["ok"])
        tools = modeling["data"]["tools"]
        self.assertEqual("available", tools["surface_scatter"]["status"])
        self.assertEqual("available", tools["boolean_cut_preview"]["status"])
        self.assertEqual("available", tools["mesh_cleanup"]["status"])
        self.assertEqual("blender.live_mesh_cleanup", tools["mesh_cleanup"]["action"])
        self.assertIn("expected_base_geometry_sha256_matches", tools["mesh_cleanup"]["runtime_requirements"])
        self.assertIn("no_modifiers", tools["mesh_cleanup"]["runtime_requirements"])
        self.assertEqual("available", tools["degenerate_repair_preview"]["status"])
        self.assertEqual(
            "blender.live_degenerate_repair_preview",
            tools["degenerate_repair_preview"]["action"],
        )
        self.assertEqual(
            {
                "commit": "blender.live_degenerate_repair_commit",
                "cancel": "blender.live_degenerate_repair_cancel",
            },
            tools["degenerate_repair_preview"]["workflow_actions"],
        )
        self.assertEqual("available", tools["merge_by_distance_preview"]["status"])
        self.assertEqual(
            {
                "commit": "blender.live_merge_by_distance_commit",
                "cancel": "blender.live_merge_by_distance_cancel",
            },
            tools["merge_by_distance_preview"]["workflow_actions"],
        )
        self.assertEqual(
            {"commit": "blender.live_boolean_cut_commit", "cancel": "blender.live_boolean_cut_cancel"},
            tools["boolean_cut_preview"]["workflow_actions"],
        )

    def test_blender_prepare_adopts_existing_window_without_starting_blender(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (root / "agent-settings.json").write_text(json.dumps({
                "default_project": "demo",
                "projects": {"demo": {"path": str(project), "apps": ["blender"], "blender": {}}},
            }), encoding="utf-8")
            env = {
                "ORDAX_AGENT_STATE_DIR": str(root),
                "ORDAX_MEMORY_DB": str(root / "memory.db"),
            }
            with patch.dict(os.environ, env, clear=False):
                api = StudioApi()
                with patch.object(api.agent, "execute") as execute:
                    execute.side_effect = [
                        ActionResult(False, "not connected", {}),
                        ActionResult(True, "Existing Blender window adopted by ORDAX Studio", {
                            "pid": 4242,
                            "presence": {"pid": 4242, "file": str(project / "scene.blend")},
                        }),
                    ]
                    result = api.blender_prepare()
            self.assertTrue(result["ok"])
            self.assertEqual("adopted", result["data"]["state"])
            self.assertEqual(4242, result["data"]["pid"])
            self.assertEqual(
                ["blender.live_status", "blender.adopt"],
                [call.args[0] for call in execute.call_args_list],
            )

    def test_blender_prepare_reports_running_unmanaged_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (root / "agent-settings.json").write_text(json.dumps({
                "default_project": "demo",
                "projects": {"demo": {"path": str(project), "apps": ["blender"], "blender": {}}},
            }), encoding="utf-8")
            env = {"ORDAX_AGENT_STATE_DIR": str(root), "ORDAX_MEMORY_DB": str(root / "memory.db")}
            with patch.dict(os.environ, env, clear=False):
                api = StudioApi()
                with patch.object(api.agent, "execute") as execute:
                    execute.side_effect = [
                        ActionResult(False, "not connected", {}),
                        ActionResult(False, "no match", {"no_match": True}),
                        ActionResult(True, "instances", {"unmanaged_blender_pids": [7777]}),
                    ]
                    result = api.blender_prepare()
            self.assertTrue(result["ok"])
            self.assertEqual("restart_required", result["data"]["state"])
            self.assertEqual([7777], result["data"]["blender_pids"])
            self.assertEqual(
                ["blender.live_status", "blender.adopt", "blender.instances"],
                [call.args[0] for call in execute.call_args_list],
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
        self.assertIn("blender_prepare", script)
        self.assertIn("MODELAGEM BLENDER TIPADA", script)
        self.assertIn("workflow_actions", script)
        self.assertIn("state.bootstrap?.modeling", script)
        self.assertIn("adotado", script)
        self.assertIn("preview_start", script)
        self.assertIn("preview_capture", script)
        self.assertIn("workspaceProjectList", stylesheet)
        self.assertIn("previewFocus", stylesheet)


if __name__ == "__main__":
    unittest.main()
