from __future__ import annotations

import unittest
from pathlib import Path


class OpenAiReviewGrantWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.workflow = (
            root / ".github" / "workflows" / "openai-review-grant.yml"
        ).read_text(encoding="utf-8")

    def test_review_grant_is_fixed_to_demo_project_and_bounded_actions(self) -> None:
        self.assertIn(
            "ORDAX_OPERATOR_TOKEN: ${{ secrets.ORDAX_OPERATOR_TOKEN }}",
            self.workflow,
        )
        self.assertIn("/v3/product-grants/from-link", self.workflow)
        self.assertIn('"projects": ["ordax-review-demo"]', self.workflow)
        self.assertIn("timedelta(days=30)", self.workflow)
        expected = (
            '"computer.access_status"',
            '"computer.active_window"',
            '"computer.click"',
            '"computer.focus_window"',
            '"computer.launch_app"',
            '"computer.mouse_move"',
            '"computer.processes"',
            '"computer.screen_info"',
            '"computer.screenshot"',
            '"computer.scroll"',
            '"computer.type"',
            '"git.status"',
            '"project.search_text"',
            '"project.text_read"',
            '"project.text_write"',
            '"projects.list"',
        )
        for action in expected:
            self.assertIn(action, self.workflow)

        for forbidden in (
            '"computer.hotkey",',
            '"computer.terminate_process",',
            '"git.command",',
            '"process.start",',
            '"process.stop",',
            '"terminal.exec",',
        ):
            self.assertNotIn(forbidden, self.workflow.split("forbidden_actions =", 1)[0])
        self.assertIn('forbidden_actions = {', self.workflow)

    def test_operator_secret_is_not_a_dispatch_input(self) -> None:
        dispatch = self.workflow.split("permissions:", 1)[0]
        self.assertIn("link_id:", dispatch)
        self.assertNotIn("operator_token", dispatch.lower())
        self.assertIn("environment: cloudflare-v3", self.workflow)
        self.assertIn("set -euo pipefail", self.workflow)


if __name__ == "__main__":
    unittest.main()
