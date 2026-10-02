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
            "workspace.project_create",
            "project.inventory",
            "project.text_read",
            "handoff.get",
            "handoff.create",
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
            "agent.project_briefing",
            "continuity.get",
            "continuity.update",
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
                "project_create",
                "repository_catalog",
                "project_inventory",
                "project_text_read",
                "handoff_get",
                "handoff_create",
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
                "project_briefing",
                "continuity_state",
                "continuity_update",
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
        self.assertEqual(effects["project_create"], "write")
        self.assertEqual(effects["project_briefing"], "read")
        self.assertEqual(effects["continuity_state"], "read")
        self.assertEqual(effects["continuity_update"], "write")
        self.assertEqual(effects["git_status"], "read")
        self.assertEqual(effects["project_text_write"], "write")
        self.assertEqual(effects["handoff_get"], "read")
        self.assertEqual(effects["handoff_create"], "write")
        self.assertEqual(effects["workspace_text_write"], "write")
        self.assertEqual(effects["terminal_exec"], "execute")
        self.assertEqual(effects["git_command"], "execute")
        self.assertEqual(effects["blender_transform"], "write")

        descriptions = {tool["name"]: tool["description"] for tool in tools}
        self.assertIn("continue/resume", descriptions["projects_list"])
        self.assertIn("fresh chat", descriptions["project_briefing"])
        self.assertIn("pass the user intent as query", descriptions["project_briefing"])

    def test_durable_continuity_tools_are_project_scoped(self):
        loaded = self.facade.call(
            "continuity_state",
            {"project": "demo"},
            context=self.context,
            grant=self.grant("continuity.get"),
        )
        self.assertTrue(loaded.ok)
        self.assertEqual(self.executor.calls[-1], ("continuity.get", {"project": "demo"}))

        updated = self.facade.call(
            "continuity_update",
            {"project": "demo", "summary": "Ready", "next_action": "Ship"},
            context=self.context,
            grant=self.grant("continuity.update"),
        )
        self.assertTrue(updated.ok)
        self.assertEqual(
            self.executor.calls[-1],
            ("continuity.update", {"project": "demo", "summary": "Ready", "next_action": "Ship"}),
        )

    def test_project_create_is_global_but_requires_its_explicit_grant(self):
        result = self.facade.call(
            "project_create",
            {"slug": "new-app", "apps": [], "git_init": True},
            context=self.context,
            grant=self.grant("workspace.project_create"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            self.executor.calls,
            [("workspace.project_create", {"slug": "new-app", "apps": [], "git_init": True})],
        )

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
