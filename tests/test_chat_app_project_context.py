from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ordax_chat_app.project_context import ProjectContextLoader


class ProjectContextLoaderTests(unittest.TestCase):
    def test_loads_rules_and_skills_in_deterministic_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("Root rules", encoding="utf-8")
            rules = root / ".ordax" / "rules"
            rules.mkdir(parents=True)
            (rules / "backend.md").write_text("Backend rules", encoding="utf-8")
            skill = root / ".ordax" / "skills" / "testing"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("Testing skill", encoding="utf-8")

            context = ProjectContextLoader().load(root)

            self.assertEqual(
                [item.relative_path for item in context.documents],
                [
                    "AGENTS.md",
                    ".ordax/rules/backend.md",
                    ".ordax/skills/testing/SKILL.md",
                ],
            )
            self.assertEqual(
                [item.kind for item in context.documents],
                ["rules", "rules", "skill"],
            )
            block = context.instructions_block()
            self.assertIn("Root rules", block)
            self.assertIn("Backend rules", block)
            self.assertIn("Testing skill", block)

    def test_context_is_bounded_and_marks_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("x" * 1000, encoding="utf-8")
            context = ProjectContextLoader(
                max_total_bytes=128,
                max_file_bytes=128,
            ).load(root)
            self.assertTrue(context.truncated)
            self.assertLessEqual(context.total_bytes, 128)

    def test_git_internals_are_never_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hidden = root / ".git" / "nested"
            hidden.mkdir(parents=True)
            (hidden / "AGENTS.md").write_text("secret", encoding="utf-8")
            context = ProjectContextLoader().load(root)
            self.assertEqual(context.documents, ())


if __name__ == "__main__":
    unittest.main()
