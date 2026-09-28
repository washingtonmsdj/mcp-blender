import json
import tempfile
import unittest
from pathlib import Path

from ordax_core.memory import MemoryStore


class OrdaxCoreMemoryTests(unittest.TestCase):
    def test_project_memory_survives_store_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            db = root / "state.db"

            first = MemoryStore(db)
            memory_id = first.remember("demo", project, "Use metric scale", "decision")
            task_id = first.add_task("demo", project, "Create Blender scene")
            checkpoint_id = first.checkpoint("demo", project, "Foundation created")

            self.assertGreater(memory_id, 0)
            self.assertGreater(task_id, 0)
            self.assertGreater(checkpoint_id, 0)

            reopened = MemoryStore(db)
            context = reopened.context("demo", project)
            self.assertEqual(context["project"]["slug"], "demo")
            self.assertEqual(context["memories"][0]["content"], "Use metric scale")
            self.assertEqual(context["tasks"][0]["title"], "Create Blender scene")
            self.assertFalse(context["tasks"][0]["done"])
            self.assertEqual(context["checkpoints"][0]["summary"], "Foundation created")

            done = reopened.toggle_task("demo", project, task_id)
            self.assertTrue(done)
            final = reopened.context("demo", project)
            self.assertTrue(final["tasks"][0]["done"])

            context_path = reopened.write_context("demo", project)
            text = context_path.read_text(encoding="utf-8")
            self.assertIn("ORDAX Studio", text)
            self.assertIn("Use metric scale", text)
            self.assertIn("Create Blender scene", text)

    def test_status_reports_database_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            store = MemoryStore(root / "state.db")
            store.remember("demo", project, "Persistent fact")
            status = store.status()
            self.assertTrue(status["ok"])
            self.assertEqual(status["counts"]["projects"], 1)
            self.assertEqual(status["counts"]["memories"], 1)
            json.dumps(status)


    def test_session_resume_persists_active_project_and_boot_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            store = MemoryStore(root / "state.db")
            store.remember("demo", project, "Keep session continuity", "decision")
            checkpoint_id = store.checkpoint("demo", project, "Ready to resume")
            session = store.start_session("demo", project)
            self.assertGreater(session["session_id"], 0)
            self.assertEqual(session["resumed_from_checkpoint_id"], checkpoint_id)
            self.assertEqual(store.active_project()["name"], "demo")
            boot = Path(session["boot_context_path"])
            self.assertTrue(boot.is_file())
            self.assertIn("Keep session continuity", boot.read_text(encoding="utf-8"))

            reopened = MemoryStore(root / "state.db")
            self.assertEqual(reopened.active_project()["name"], "demo")
            self.assertTrue(reopened.finish_session(session["session_id"]))
            self.assertFalse(reopened.finish_session(session["session_id"]))
            self.assertEqual(reopened.status()["counts"]["sessions"], 1)


if __name__ == "__main__":
    unittest.main()
