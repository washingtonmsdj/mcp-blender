from __future__ import annotations

import unittest
from pathlib import Path


class OpenAiReviewGrantWorkflowTests(unittest.TestCase):
    def test_review_grant_is_fixed_to_demo_project_and_bounded_actions(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (
            root / ".github" / "workflows" / "openai-review-grant.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("ORDAX_OPERATOR_TOKEN: ${{ secrets.ORDAX_OPERATOR_TOKEN }}", workflow)
        self.assertIn("/v3/product-grants/from-link", workflow)
        self.assertIn('"projects": ["ordax-review-demo"]', workflow)
        self.assertIn("timedelta(days=30)", workflow)
        for action in (
            '"git.status"',
            '"project.search_text"',
            '"project.text_read"',
            '"project.text_write"',
            '"projects.list"',
        ):
            self.assertIn(action, workflow)
        self.assertIn('if "terminal.exec" in grant.get("actions", [])', workflow)
        self.assertNotIn('"terminal.exec",', workflow)
        self.assertNotIn('"git.command"', workflow)
        self.assertNotIn('"terminal_exec"', workflow)


if __name__ == "__main__":
    unittest.main()
