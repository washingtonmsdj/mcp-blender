from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ordax_dev_agent import product_mcp_server as server


class FakeClient:
    instances = []

    def __init__(self, base_url):
        self.base_url = base_url
        self.calls = []
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def session(self, token):
        self.calls.append(("session", token))
        return {"subject_id": "user:1"}

    def targets(self, token, *, space_id=None):
        self.calls.append(("targets", token, space_id))
        return [{"device_id": "dev-1", "grants": []}]

    def submit_action(self, token, **kwargs):
        self.calls.append(("submit", token, kwargs))
        return "req-1"

    def wait_action(self, token, request_id):
        self.calls.append(("wait", token, request_id))
        return {
            "request_id": request_id,
            "status": "succeeded",
            "result": {"ok": True, "data": {"branch": "main"}},
            "error_code": None,
        }


class ProductMcpServerTests(unittest.TestCase):
    def setUp(self):
        FakeClient.instances.clear()
        self.env = patch.dict(
            os.environ,
            {
                "ORDAX_PRODUCT_ACCESS_TOKEN": "jwt-secret",
                "ORDAX_PRODUCT_CONTROL_PLANE_URL": "https://control.example.test",
            },
            clear=False,
        )
        self.client = patch.object(server, "ProductRemoteClient", FakeClient)
        self.env.start()
        self.client.start()

    def tearDown(self):
        self.client.stop()
        self.env.stop()

    def test_session_and_targets_use_environment_token(self):
        self.assertEqual(server.product_session()["subject_id"], "user:1")
        targets = server.product_targets("space-1")
        self.assertEqual(targets[0]["device_id"], "dev-1")
        calls = [call for instance in FakeClient.instances for call in instance.calls]
        self.assertIn(("session", "jwt-secret"), calls)
        self.assertIn(("targets", "jwt-secret", "space-1"), calls)

    def test_explicit_read_only_tool_routes_via_remote_client(self):
        result = server.git_status("dev-1", "demo", "space-1")
        self.assertEqual(result["status"], "succeeded")
        calls = [call for instance in FakeClient.instances for call in instance.calls]
        submit = next(call for call in calls if call[0] == "submit")
        self.assertEqual(submit[1], "jwt-secret")
        self.assertEqual(submit[2]["device_id"], "dev-1")
        self.assertEqual(submit[2]["action"], "git.status")
        self.assertEqual(submit[2]["project"], "demo")
        self.assertEqual(submit[2]["arguments"], {"project": "demo"})
        self.assertIn(("wait", "jwt-secret", "req-1"), calls)

    def test_project_create_routes_as_global_typed_write(self):
        result = server.project_create(
            "dev-1",
            "new-app",
            "New App",
            ["blender"],
            True,
            True,
            True,
            "space-1",
        )
        self.assertEqual(result["status"], "succeeded")
        calls = [call for instance in FakeClient.instances for call in instance.calls]
        submit = next(call for call in calls if call[0] == "submit")
        self.assertEqual(submit[2]["action"], "workspace.project_create")
        self.assertIsNone(submit[2]["project"])
        self.assertEqual(
            submit[2]["arguments"],
            {
                "slug": "new-app",
                "name": "New App",
                "apps": ["blender"],
                "set_default": True,
                "git_init": True,
                "readme": True,
            },
        )

    def test_project_briefing_and_continuity_route_with_project_scope(self):
        briefing = server.project_briefing("dev-1", "demo", "space-1")
        self.assertEqual(briefing["status"], "succeeded")
        state = server.continuity_state("dev-1", "demo", "space-1")
        self.assertEqual(state["status"], "succeeded")
        updated = server.continuity_update(
            "dev-1", "demo", "Ready", "Ship", ["foundation"], [], ["src/app.py"], "space-1"
        )
        self.assertEqual(updated["status"], "succeeded")

        calls = [call for instance in FakeClient.instances for call in instance.calls if call[0] == "submit"]
        actions = [call[2]["action"] for call in calls]
        self.assertIn("agent.project_briefing", actions)
        self.assertIn("continuity.get", actions)
        self.assertIn("continuity.update", actions)
        update = next(call for call in calls if call[2]["action"] == "continuity.update")
        self.assertEqual(update[2]["project"], "demo")
        self.assertEqual(update[2]["arguments"]["summary"], "Ready")
        self.assertEqual(update[2]["arguments"]["next_action"], "Ship")

    def test_studio_catalog_routes_without_project_scope(self):
        result = server.repository_catalog("dev-1", "space-1")
        self.assertEqual(result["status"], "succeeded")
        calls = [call for instance in FakeClient.instances for call in instance.calls]
        submit = next(call for call in calls if call[0] == "submit")
        self.assertEqual(submit[2]["action"], "workspace.repository_catalog")
        self.assertIsNone(submit[2]["project"])
        self.assertEqual(submit[2]["arguments"], {})

    def test_typed_mutations_are_exposed_but_generic_execution_is_not(self):
        for name in (
            "project_create", "continuity_update", "project_text_write", "project_text_patch", "blender_start",
            "blender_transform", "blender_create_primitive",
            "blender_apply_material", "blender_save",
        ):
            self.assertTrue(hasattr(server, name), name)
        for name in ("action_execute", "shell_exec", "blender_run_python"):
            self.assertFalse(hasattr(server, name), name)

    def test_token_is_required_but_never_a_tool_parameter(self):
        for name in (
            "product_session",
            "product_targets",
            "projects_list",
            "project_create",
            "repository_catalog",
            "project_inventory",
            "project_text_read",
            "project_health",
            "project_briefing",
            "continuity_state",
            "continuity_update",
            "project_search",
            "project_read_batch",
            "project_preview_status",
            "git_status",
            "git_diff",
            "artifacts_list",
            "artifact_preview",
        ):
            annotations = getattr(server, name).__annotations__
            self.assertNotIn("access_token", annotations)
            self.assertNotIn("token", annotations)

        with patch.dict(os.environ, {"ORDAX_PRODUCT_ACCESS_TOKEN": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                server.product_session()


if __name__ == "__main__":
    unittest.main()
