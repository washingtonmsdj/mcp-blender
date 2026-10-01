from __future__ import annotations

import unittest

from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.product_gateway import (
    ProductActionGateway,
    ProductGrant,
    ProductRequestContext,
)
from ordax_dev_agent.product_mcp import ProductMcpFacade


class _Executor:
    def __init__(self):
        self.calls = []
        self._names = [
            "projects.list",
            "workspace.repository_catalog",
            "project.inventory",
            "project.text_read",
            "workspace.file_stat",
            "workspace.directory_list",
            "workspace.text_read",
            "workspace.text_write",
            "workspace.text_patch",
            "workspace.directory_create",
            "workspace.path_remove",
            "workspace.path_move",
            "git.command",
            "terminal.exec",
            "project.search_text",
            "project.text_read_batch",
            "project.preview_status",
            "agent.project_health",
            "artifacts.list",
            "git.status",
            "git.diff",
            "artifact.preview",
            "project.text_write",
            "project.text_patch",
            "blender.live_status",
            "blender.live_scene_snapshot",
            "blender.live_object_inspect",
            "blender.live_modeling_schema",
            "blender.live_start",
            "blender.live_object_transform",
            "blender.live_create_primitive",
            "blender.live_material_apply",
            "blender.live_save",
        ]

    @property
    def names(self):
        return list(self._names)

    def execute(self, action, payload):
        self.calls.append((action, dict(payload)))
        return ActionResult(True, "ok", {"project_root": "C:/secret", "branch": "main"})


class _Audit:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


class ProductMcpFacadeTests(unittest.TestCase):
    def setUp(self):
        self.executor = _Executor()
        self.audit = _Audit()
        self.gateway = ProductActionGateway(self.executor, self.audit, clock=lambda: 1000)
        self.facade = ProductMcpFacade(self.gateway)
        self.context = ProductRequestContext(
            request_id="req-1",
            subject_id="user:1",
            device_id="device-1",
            space_id="space-1",
        )

    def grant(self, *actions):
        return ProductGrant(
            grant_id="grant-1",
            subject_id="user:1",
            actions=frozenset(actions),
            projects=frozenset({"demo"}),
            device_id="device-1",
            space_id="space-1",
            expires_at_unix=2000,
        )

    def test_catalog_is_capability_typed_and_derived_from_gateway(self):
        tools = self.facade.tools()
        names = {tool["name"] for tool in tools}

        self.assertEqual(
            names,
            {
                "projects_list",
                "repository_catalog",
                "project_inventory",
                "project_text_read",
                "workspace_file_stat",
                "workspace_directory_list",
                "workspace_text_read",
                "workspace_text_write",
                "workspace_text_patch",
                "workspace_directory_create",
                "workspace_path_remove",
                "workspace_path_move",
                "git_command",
                "terminal_exec",
                "project_health",
                "project_search",
                "project_read_batch",
                "project_preview_status",
                "artifacts_list",
                "git_status",
                "git_diff",
                "artifact_preview",
                "project_text_write", "project_text_patch", "blender_status",
                "blender_scene_snapshot", "blender_object_inspect", "blender_modeling_schema",
                "blender_start", "blender_transform", "blender_create_primitive",
                "blender_apply_material", "blender_save",
            },
        )
        effects = {tool["name"]: tool["effect"] for tool in tools}
        self.assertEqual(effects["git_status"], "read")
        self.assertEqual(effects["project_text_write"], "write")
        self.assertEqual(effects["workspace_text_write"], "write")
        self.assertEqual(effects["terminal_exec"], "execute")
        self.assertEqual(effects["git_command"], "execute")
        self.assertEqual(effects["blender_transform"], "write")

    def test_call_routes_through_gateway_and_preserves_audit(self):
        result = self.facade.call(
            "git_status",
            {"project": "demo"},
            context=self.context,
            grant=self.grant("git.status"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(self.executor.calls, [("git.status", {"project": "demo"})])
        self.assertEqual(len(self.audit.events), 2)

    def test_facade_cannot_bypass_gateway_grants(self):
        result = self.facade.call(
            "git_status",
            {"project": "demo"},
            context=self.context,
            grant=self.grant("projects.list"),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "grant_required")
        self.assertEqual(self.executor.calls, [])

    def test_mutation_and_unknown_tools_are_not_exposed(self):
        for tool_name in ("git_sync", "blender_run_python", "shell_exec", "action_execute"):
            result = self.facade.call(
                tool_name,
                {"project": "demo"},
                context=self.context,
                grant=self.grant("*"),
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.data["error_code"], "product_mcp_tool_not_exposed")

        self.assertEqual(self.executor.calls, [])


if __name__ == "__main__":
    unittest.main()
