import hashlib
import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


class ProjectTextActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        (self.project / "Assets" / "Scripts").mkdir(parents=True)
        self.config = AgentConfig(
            "test",
            None,
            None,
            5,
            self.root / "state",
            self.root / "agent",
            self.root / "hordax",
            self.root / "bridge",
            projects={"project": {"path": str(self.project), "apps": ["unity"]}},
            default_project="project",
        )
        self.registry = ActionRegistry(self.config)

    def test_read_and_sha_guarded_write(self) -> None:
        target = self.project / "Assets" / "Scripts" / "World.cs"
        target.write_bytes(b"class World {}\n")

        read = self.registry.execute(
            "project.text_read",
            {"path": "Assets/Scripts/World.cs"},
        )
        self.assertTrue(read.ok)
        self.assertEqual("class World {}\n", read.data["content"])
        self.assertEqual(
            hashlib.sha256(target.read_bytes()).hexdigest(),
            read.data["sha256"],
        )

        write = self.registry.execute(
            "project.text_write",
            {
                "path": "Assets/Scripts/World.cs",
                "expected_sha256": read.data["sha256"],
                "content": "class World { int Version = 2; }\n",
            },
        )
        self.assertTrue(write.ok)
        self.assertFalse(write.data["created"])
        self.assertEqual(
            "class World { int Version = 2; }\n",
            target.read_bytes().decode("utf-8"),
        )

    def test_stale_write_is_refused(self) -> None:
        target = self.project / "Assets" / "Scripts" / "World.cs"
        target.write_text("first\n", encoding="utf-8")
        read = self.registry.execute(
            "project.text_read",
            {"path": "Assets/Scripts/World.cs"},
        )
        target.write_text("human edit\n", encoding="utf-8")

        result = self.registry.execute(
            "project.text_write",
            {
                "path": "Assets/Scripts/World.cs",
                "expected_sha256": read.data["sha256"],
                "content": "remote edit\n",
            },
        )
        self.assertFalse(result.ok)
        self.assertIn("stale overwrite", result.summary)
        self.assertEqual("human edit\n", target.read_text(encoding="utf-8"))


    def test_sha_guarded_exact_patch(self) -> None:
        target = self.project / "Assets" / "Scripts" / "World.cs"
        target.write_text(
            "class World { int Version = 1; int Count = 1; }\n",
            encoding="utf-8",
        )
        read = self.registry.execute(
            "project.text_read",
            {"path": "Assets/Scripts/World.cs"},
        )

        patch_result = self.registry.execute(
            "project.text_patch",
            {
                "path": "Assets/Scripts/World.cs",
                "expected_sha256": read.data["sha256"],
                "replacements": [
                    {
                        "old": "int Version = 1;",
                        "new": "int Version = 2;",
                        "expected_count": 1,
                    },
                    {
                        "old": "int Count = 1;",
                        "new": "int Count = 3;",
                    },
                ],
            },
        )

        self.assertTrue(patch_result.ok)
        self.assertEqual(2, patch_result.data["replacement_count"])
        self.assertEqual(
            "class World { int Version = 2; int Count = 3; }\n",
            target.read_text(encoding="utf-8"),
        )

    def test_patch_refuses_ambiguous_or_stale_matches(self) -> None:
        target = self.project / "Assets" / "Scripts" / "World.cs"
        target.write_text("x x\n", encoding="utf-8")
        read = self.registry.execute(
            "project.text_read",
            {"path": "Assets/Scripts/World.cs"},
        )

        ambiguous = self.registry.execute(
            "project.text_patch",
            {
                "path": "Assets/Scripts/World.cs",
                "expected_sha256": read.data["sha256"],
                "replacements": [{"old": "x", "new": "y", "expected_count": 1}],
            },
        )
        self.assertFalse(ambiguous.ok)
        self.assertIn("ambiguous patch", ambiguous.summary)
        self.assertEqual("x x\n", target.read_text(encoding="utf-8"))

        target.write_text("human edit\n", encoding="utf-8")
        stale = self.registry.execute(
            "project.text_patch",
            {
                "path": "Assets/Scripts/World.cs",
                "expected_sha256": read.data["sha256"],
                "replacements": [{"old": "human", "new": "remote"}],
            },
        )
        self.assertFalse(stale.ok)
        self.assertIn("stale patch", stale.summary)
        self.assertEqual("human edit\n", target.read_text(encoding="utf-8"))

    def test_create_requires_explicit_flag(self) -> None:
        payload = {
            "path": "Assets/Scripts/NewTool.cs",
            "content": "class NewTool {}\n",
        }
        self.assertFalse(self.registry.execute("project.text_write", payload).ok)
        payload["create"] = True
        result = self.registry.execute("project.text_write", payload)
        self.assertTrue(result.ok)
        self.assertTrue(result.data["created"])

    def test_serialized_unity_assets_are_read_only(self) -> None:
        scene = self.project / "Assets" / "Scene.unity"
        scene.write_text("%YAML 1.1\n", encoding="utf-8")
        read = self.registry.execute(
            "project.text_read",
            {"path": "Assets/Scene.unity"},
        )
        self.assertTrue(read.ok)
        write = self.registry.execute(
            "project.text_write",
            {
                "path": "Assets/Scene.unity",
                "expected_sha256": read.data["sha256"],
                "content": "%YAML 1.1\n---\n",
            },
        )
        self.assertFalse(write.ok)
        self.assertIn("not writable", write.summary)

    def test_generated_and_escaped_paths_are_refused(self) -> None:
        (self.project / "Library").mkdir()
        (self.project / "Library" / "Generated.cs").write_text(
            "class Generated {}\n",
            encoding="utf-8",
        )
        self.assertFalse(
            self.registry.execute(
                "project.text_read",
                {"path": "Library/Generated.cs"},
            ).ok
        )
        self.assertFalse(
            self.registry.execute(
                "project.text_read",
                {"path": "../outside.cs"},
            ).ok
        )


if __name__ == "__main__":
    unittest.main()
