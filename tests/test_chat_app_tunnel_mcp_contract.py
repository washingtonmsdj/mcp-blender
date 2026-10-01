from __future__ import annotations

import unittest
from pathlib import Path

from ordax_chat_app.web_bridge import WebBridgeManager


class TunnelMcpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.source = (root / "ordax_chat_app" / "tunnel_mcp_server.py").read_text(encoding="utf-8")
        cls.bridge = (root / "ordax_chat_app" / "web_bridge.py").read_text(encoding="utf-8")

    def test_tunnel_uses_dedicated_restricted_server(self) -> None:
        command = WebBridgeManager._python_command()
        self.assertIn("-m ordax_chat_app.tunnel_mcp_server", command)
        self.assertNotIn("ordax_studio.mcp_server", command)

    def test_tunnel_surface_has_explicit_tools_and_no_generic_executor(self) -> None:
        for name in (
            "projects_list",
            "handoff_get",
            "handoff_create",
            "project_search",
            "project_read_batch",
            "workspace_text_read",
            "workspace_text_write",
            "workspace_text_patch",
            "workspace_path_move",
            "workspace_path_remove",
            "git_status",
            "git_diff",
            "git_command",
            "terminal_exec",
            "project_preview_status",
        ):
            self.assertIn(f"def {name}(", self.source)

        self.assertNotIn("def action_execute(", self.source)
        self.assertNotIn("blender.run_python", self.source)
        self.assertNotIn("workspace.list_projects", self.source)

    def test_every_mutating_tool_is_project_scoped(self) -> None:
        self.assertIn('_call("workspace.text_write", project', self.source)
        self.assertIn('_call("workspace.text_patch", project', self.source)
        self.assertIn('_call("git.command", project', self.source)
        self.assertIn('_call("terminal.exec", project', self.source)
        self.assertIn('_call("handoff.create",\n        project', self.source)


if __name__ == "__main__":
    unittest.main()
