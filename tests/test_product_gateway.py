from __future__ import annotations

import unittest
from typing import Any

from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.product_gateway import (
    PRODUCT_READ_ONLY_ACTIONS,
    ProductActionGateway,
    ProductGrant,
    product_action_catalog,
)


class FakeExecutor:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._names = [
            "projects.list",
            "project.inventory",
            "project.text_read",
            "project.text_write",
            "git.status",
            "git.diff",
            "git.sync",
            "artifact.preview",
            "artifact.read_chunk",
            "blender.live_inspect",
            "unity.scene_summary",
        ]

    @property
    def names(self) -> list[str]:
        return list(self._names)

    def execute(self, action: str, payload: dict[str, Any]) -> ActionResult:
        self.calls.append((action, payload))
        if action == "projects.list":
            return ActionResult(
                True,
                "projects",
                {
                    "default_project": "scene",
                    "projects": [
                        {
                            "slug": "scene",
                            "path": "C:/Users/example/secret/project",
                            "apps": ["blender"],
                            "available": True,
                            "allowed_branches": ["main"],
                            "unity": {"allowed_methods": ["x"]},
                            "blender": {"blend_file": "private.blend"},
                        }
                    ],
                },
            )
        if action == "project.inventory":
            return ActionResult(
                True,
                "inventory",
                {
                    "project": "scene",
                    "project_root": "C:/Users/example/secret/project",
                    "entries": [{"path": "docs/README.md", "kind": "file"}],
                },
            )
        if action in {"git.status", "git.diff"}:
            return ActionResult(
                True,
                "git",
                {
                    "stdout": "",
                    "stderr": "",
                    "returncode": 0,
                    "command": ["git", "-C", "C:/Users/example/secret/project", "status"],
                },
            )
        if action == "artifact.preview":
            return ActionResult(
                True,
                "preview",
                {
                    "artifact_name": "preview.png",
                    "path": "C:/Users/example/AppData/Local/OrdaX/artifacts/scene/preview.png",
                    "mime_type": "image/png",
                    "base64": "AA==",
                },
            )
        return ActionResult(True, "ok", {"payload": payload})


class ProductGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = FakeExecutor()
        self.gateway = ProductActionGateway(self.executor)

    def test_catalog_contains_only_explicit_read_only_surface(self) -> None:
        names = {entry["name"] for entry in product_action_catalog()}
        self.assertEqual(names, set(PRODUCT_READ_ONLY_ACTIONS))
        self.assertIn("project.text_read", names)
        self.assertIn("git.diff", names)
        self.assertNotIn("project.text_write", names)
        self.assertNotIn("git.sync", names)
        self.assertNotIn("artifact.read_chunk", names)
        self.assertFalse(any(name.startswith("blender.") for name in names))
        self.assertFalse(any(name.startswith("unity.") for name in names))

    def test_action_requires_explicit_action_grant(self) -> None:
        result = self.gateway.execute(
            "project.text_read",
            {"project": "scene", "path": "docs/README.md"},
            grant=ProductGrant(actions=frozenset(), projects=frozenset({"scene"})),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "grant_required")
        self.assertEqual(self.executor.calls, [])

    def test_project_scoped_action_requires_project_grant(self) -> None:
        result = self.gateway.execute(
            "git.status",
            {"project": "scene"},
            grant=ProductGrant(actions=frozenset({"git.status"})),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "project_grant_required")
        self.assertEqual(self.executor.calls, [])

    def test_unsupported_payload_field_is_rejected_before_execution(self) -> None:
        result = self.gateway.execute(
            "git.status",
            {"project": "scene", "command": "whoami"},
            grant=ProductGrant(
                actions=frozenset({"git.status"}),
                projects=frozenset({"scene"}),
            ),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "invalid_product_action_payload")
        self.assertEqual(self.executor.calls, [])

    def test_mutating_or_bulk_actions_are_not_exposed_even_if_granted(self) -> None:
        grant = ProductGrant(
            actions=frozenset(
                {"project.text_write", "git.sync", "artifact.read_chunk", "blender.live_inspect"}
            ),
            projects=frozenset({"scene"}),
        )
        for action in grant.actions:
            result = self.gateway.execute(action, {"project": "scene"}, grant=grant)
            self.assertFalse(result.ok)
            self.assertIn("not exposed", result.summary)
        self.assertEqual(self.executor.calls, [])

    def test_global_project_catalog_redacts_workstation_paths_and_private_adapter_config(self) -> None:
        result = self.gateway.execute(
            "projects.list",
            {},
            grant=ProductGrant(actions=frozenset({"projects.list"})),
        )

        self.assertTrue(result.ok)
        project = result.data["projects"][0]
        self.assertEqual(project["slug"], "scene")
        self.assertNotIn("path", project)
        self.assertNotIn("unity", project)
        self.assertNotIn("blender", project)

    def test_inventory_redacts_absolute_project_root(self) -> None:
        result = self.gateway.execute(
            "project.inventory",
            {"project": "scene"},
            grant=ProductGrant(
                actions=frozenset({"project.inventory"}),
                projects=frozenset({"scene"}),
            ),
        )

        self.assertTrue(result.ok)
        self.assertNotIn("project_root", result.data)
        self.assertEqual(result.data["entries"][0]["path"], "docs/README.md")

    def test_git_results_redact_absolute_command(self) -> None:
        result = self.gateway.execute(
            "git.status",
            {"project": "scene"},
            grant=ProductGrant(
                actions=frozenset({"git.status"}),
                projects=frozenset({"scene"}),
            ),
        )

        self.assertTrue(result.ok)
        self.assertNotIn("command", result.data)

    def test_artifact_preview_redacts_local_absolute_path(self) -> None:
        result = self.gateway.execute(
            "artifact.preview",
            {"project": "scene", "artifact_name": "preview.png"},
            grant=ProductGrant(
                actions=frozenset({"artifact.preview"}),
                projects=frozenset({"scene"}),
            ),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.data["artifact_name"], "preview.png")
        self.assertNotIn("path", result.data)

    def test_granted_read_only_action_routes_to_existing_local_action(self) -> None:
        payload = {"project": "scene", "path": "docs/README.md"}
        result = self.gateway.execute(
            "project.text_read",
            payload,
            grant=ProductGrant(
                actions=frozenset({"project.text_read"}),
                projects=frozenset({"scene"}),
            ),
        )

        self.assertTrue(result.ok)
        self.assertEqual(self.executor.calls, [("project.text_read", payload)])


if __name__ == "__main__":
    unittest.main()
