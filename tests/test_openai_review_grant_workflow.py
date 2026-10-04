from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


class OpenAiReviewGrantWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.workflow = (
            root / ".github" / "workflows" / "openai-review-grant.yml"
        ).read_text(encoding="utf-8")
        self.plugin = json.loads(
            (root / "plugins" / "ordax-studio" / "plugin.json").read_text(encoding="utf-8")
        )
        self.mcp_http = (
            root / "control-plane" / "cloudflare" / "src" / "mcp_http.ts"
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
            '"computer.windows"',
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

    def test_review_api_client_has_explicit_product_identity(self) -> None:
        self.assertIn(
            '"User-Agent": "ORDAX-OpenAI-Review-Provisioner/1.0 '
            '(+https://github.com/washingtonmsdj/mcp-blender)"',
            self.workflow,
        )
        self.assertNotIn('"User-Agent": "Mozilla/', self.workflow)

    def test_positive_review_tools_are_covered_by_review_grant(self) -> None:
        action_block = self.workflow.split("actions = [", 1)[1].split("]", 1)[0]
        granted_actions = set(re.findall(r'"([^"]+)"', action_block))

        tool_actions: dict[str, str | None] = {}
        for line in self.mcp_http.splitlines():
            name_match = re.search(r'\{ name: "([^"]+)"', line)
            if not name_match:
                continue
            action_match = re.search(r'action: "([^"]+)"', line)
            tool_actions[name_match.group(1)] = (
                action_match.group(1) if action_match else None
            )

        positive_cases = self.plugin["extensions"]["com.openai"]["review"]["test_cases"]["positive"]
        for case in positive_cases:
            triggered = [
                item.strip()
                for item in str(case.get("tools_triggered") or "").split(",")
                if item.strip()
            ]
            self.assertTrue(triggered, case.get("description"))
            for tool in triggered:
                self.assertIn(tool, tool_actions, f"review tool missing from MCP: {tool}")
                action = tool_actions[tool]
                if action is not None:
                    self.assertIn(
                        action,
                        granted_actions,
                        f"review tool {tool} requires ungranted action {action}",
                    )


if __name__ == "__main__":
    unittest.main()
