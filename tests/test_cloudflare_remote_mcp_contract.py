from __future__ import annotations

import unittest
from pathlib import Path


class CloudflareRemoteMcpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.worker = (root / "control-plane" / "cloudflare" / "src" / "index.ts").read_text(encoding="utf-8")
        cls.mcp = (root / "control-plane" / "cloudflare" / "src" / "mcp_http.ts").read_text(encoding="utf-8")

    def test_worker_exposes_authenticated_streamable_http_mcp(self) -> None:
        self.assertIn('import { handleOrdaxMcp } from "./mcp_http";', self.worker)
        self.assertIn('url.pathname === "/mcp"', self.worker)
        self.assertIn('"/.well-known/oauth-protected-resource"', self.worker)
        self.assertIn('authorization_servers', self.worker)
        self.assertIn('session: (inner) => productSession(inner, env)', self.worker)
        self.assertIn('targets: (inner) => listProductTargets(inner, env)', self.worker)

    def test_mcp_uses_product_session_as_auth_gate(self) -> None:
        auth = self.mcp.index("const sessionProbe = await handlers.session")
        parse = self.mcp.index("const raw = await request.json()")
        self.assertLess(auth, parse)
        self.assertIn('www-authenticate', self.mcp.lower())
        self.assertIn('oauth-protected-resource', self.mcp)

    def test_mcp_exposes_typed_tools_not_generic_shell(self) -> None:
        for tool in (
            '"ordax_targets"',
            '"repository_catalog"',
            '"project_text_read"',
            '"project_text_write"',
            '"handoff_get"',
            '"handoff_create"',
            '"workspace_text_read"',
            '"workspace_text_write"',
            '"workspace_path_remove"',
            '"git_command"',
            '"terminal_exec"',
            '"blender_status"',
            '"blender_scene_snapshot"',
            '"blender_start"',
            '"blender_transform"',
            '"blender_create_primitive"',
            '"blender_apply_material"',
            '"blender_save"',
        ):
            self.assertIn(tool, self.mcp)
        self.assertNotIn('action_execute', self.mcp)
        self.assertNotIn('shell_execute', self.mcp)
        self.assertNotIn('run_command', self.mcp)
        self.assertIn('action: "terminal.exec"', self.mcp)
        self.assertIn('Requires an explicit terminal.exec grant', self.mcp)

    def test_mcp_actions_still_flow_through_product_grants(self) -> None:
        self.assertIn('handlers.createAction(createRequest)', self.mcp)
        self.assertIn('handlers.getAction(statusRequest, requestId)', self.mcp)
        self.assertIn('wait_for_completion_ms', self.mcp)
        self.assertIn('Math.min(20000', self.mcp)
        self.assertIn('call ordax_action_status', self.mcp)

    def test_mcp_supports_standard_initialize_and_tools_methods(self) -> None:
        self.assertIn('method === "initialize"', self.mcp)
        self.assertIn('protocolVersion: "2025-06-18"', self.mcp)
        self.assertIn('method === "tools/list"', self.mcp)
        self.assertIn('method === "tools/call"', self.mcp)
        self.assertIn('method === "notifications/initialized"', self.mcp)

    def test_mcp_advertises_public_review_metadata(self) -> None:
        self.assertIn("annotations: toolAnnotations(tool.name)", self.mcp)
        self.assertIn("readOnlyHint: readOnly", self.mcp)
        self.assertIn("destructiveHint: DESTRUCTIVE_TOOLS.has(name)", self.mcp)
        self.assertIn("openWorldHint: OPEN_WORLD_TOOLS.has(name)", self.mcp)
        self.assertIn("outputSchema:", self.mcp)
        self.assertIn("title: TOOL_TITLES[tool.name]", self.mcp)
        self.assertIn('"openai/toolInvocation/invoking"', self.mcp)
        self.assertIn('"openai/toolInvocation/invoked"', self.mcp)

    def test_worker_exposes_public_plugin_review_routes(self) -> None:
        self.assertIn('openAiAppsChallenge', self.worker)
        self.assertIn('publicProductPage', self.worker)
        self.assertIn('"/.well-known/openai-apps-challenge"', self.worker)


if __name__ == "__main__":
    unittest.main()
