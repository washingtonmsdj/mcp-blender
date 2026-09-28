from __future__ import annotations

import unittest
from typing import Any

from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.product_gateway import (
    PRODUCT_READ_ONLY_ACTIONS,
    ProductActionGateway,
    ProductAuditEvent,
    ProductGrant,
    ProductRequestContext,
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


class AuditSink:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.events: list[ProductAuditEvent] = []

    def record(self, event: ProductAuditEvent) -> None:
        if self.fail:
            raise RuntimeError("audit unavailable")
        self.events.append(event)


class ProductGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = FakeExecutor()
        self.audit = AuditSink()
        self.gateway = ProductActionGateway(
            self.executor,
            self.audit,
            clock=lambda: 2_000_000_000,
        )
        self.context = ProductRequestContext(
            request_id="req-1",
            subject_id="user:123",
            device_id="device-1",
            space_id="space-1",
        )

    def grant(
        self,
        *actions: str,
        projects: tuple[str, ...] = ("scene",),
        subject_id: str = "user:123",
        device_id: str | None = "device-1",
        space_id: str | None = "space-1",
        expires_at_unix: int | None = 2_000_000_100,
    ) -> ProductGrant:
        return ProductGrant(
            grant_id="grant-1",
            subject_id=subject_id,
            actions=frozenset(actions),
            projects=frozenset(projects),
            device_id=device_id,
            space_id=space_id,
            expires_at_unix=expires_at_unix,
        )

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

    def test_action_requires_explicit_action_grant_and_denial_is_audited(self) -> None:
        result = self.gateway.execute(
            "project.text_read",
            {"project": "scene", "path": "docs/README.md"},
            context=self.context,
            grant=self.grant(),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "grant_required")
        self.assertEqual(self.executor.calls, [])
        self.assertEqual(len(self.audit.events), 1)
        self.assertEqual(self.audit.events[0].decision, "deny")
        self.assertEqual(self.audit.events[0].reason, "grant_required")

    def test_project_scoped_action_requires_project_grant(self) -> None:
        result = self.gateway.execute(
            "git.status",
            {"project": "scene"},
            context=self.context,
            grant=self.grant("git.status", projects=()),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "project_grant_required")
        self.assertEqual(self.executor.calls, [])

    def test_subject_device_space_and_expiry_are_bound_to_verified_context(self) -> None:
        cases = [
            (self.grant("git.status", subject_id="user:999"), "grant_subject_mismatch"),
            (self.grant("git.status", device_id="device-2"), "grant_device_mismatch"),
            (self.grant("git.status", space_id="space-2"), "grant_space_mismatch"),
            (self.grant("git.status", expires_at_unix=2_000_000_000), "grant_expired"),
        ]
        for grant, error_code in cases:
            with self.subTest(error_code=error_code):
                result = self.gateway.execute(
                    "git.status",
                    {"project": "scene"},
                    context=self.context,
                    grant=grant,
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.data["error_code"], error_code)
        self.assertEqual(self.executor.calls, [])

    def test_invalid_request_or_grant_provenance_fails_closed(self) -> None:
        bad_context = ProductRequestContext(
            request_id="bad request with spaces",
            subject_id="user:123",
            device_id="device-1",
            space_id="space-1",
        )
        result = self.gateway.execute(
            "git.status",
            {"project": "scene"},
            context=bad_context,
            grant=self.grant("git.status"),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "invalid_request_context")

        malformed_grants = [
            ProductGrant(
                grant_id="",
                subject_id="user:123",
                actions=frozenset({"git.status"}),
                projects=frozenset({"scene"}),
            ),
            ProductGrant(
                grant_id="grant-1",
                subject_id="user:123",
                actions=["git.status"],  # type: ignore[arg-type]
                projects=frozenset({"scene"}),
            ),
            ProductGrant(
                grant_id="grant-1",
                subject_id="user:123",
                actions=frozenset({"git.status"}),
                projects=frozenset({"scene"}),
                expires_at_unix="tomorrow",  # type: ignore[arg-type]
            ),
        ]
        for bad_grant in malformed_grants:
            result = self.gateway.execute(
                "git.status",
                {"project": "scene"},
                context=self.context,
                grant=bad_grant,
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.data["error_code"], "invalid_grant_provenance")
        self.assertEqual(self.executor.calls, [])

    def test_unsupported_payload_field_is_rejected_before_execution(self) -> None:
        result = self.gateway.execute(
            "git.status",
            {"project": "scene", "command": "whoami"},
            context=self.context,
            grant=self.grant("git.status"),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "invalid_product_action_payload")
        self.assertEqual(self.executor.calls, [])

    def test_mutating_or_bulk_actions_are_not_exposed_even_if_granted(self) -> None:
        actions = (
            "project.text_write",
            "git.sync",
            "artifact.read_chunk",
            "blender.live_inspect",
        )
        grant = self.grant(*actions)
        for action in actions:
            result = self.gateway.execute(
                action,
                {"project": "scene"},
                context=self.context,
                grant=grant,
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.data["error_code"], "action_not_exposed")
        self.assertEqual(self.executor.calls, [])

    def test_audit_must_persist_authorization_before_local_execution(self) -> None:
        audit = AuditSink(fail=True)
        gateway = ProductActionGateway(
            self.executor,
            audit,
            clock=lambda: 2_000_000_000,
        )

        result = gateway.execute(
            "git.status",
            {"project": "scene"},
            context=self.context,
            grant=self.grant("git.status"),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.data["error_code"], "audit_unavailable")
        self.assertEqual(self.executor.calls, [])

    def test_success_records_authorization_and_result_without_payload_contents(self) -> None:
        payload = {"project": "scene", "path": "docs/README.md"}
        result = self.gateway.execute(
            "project.text_read",
            payload,
            context=self.context,
            grant=self.grant("project.text_read"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(self.executor.calls, [("project.text_read", payload)])
        self.assertEqual(len(self.audit.events), 2)
        before, after = self.audit.events
        self.assertEqual((before.phase, before.decision), ("decision", "allow"))
        self.assertEqual((after.phase, after.result_ok), ("result", True))
        self.assertEqual(before.payload_fields, ("path", "project"))
        self.assertNotIn("README", repr(before))
        self.assertEqual(before.grant_id, "grant-1")
        self.assertEqual(before.subject_id, "user:123")

    def test_global_project_catalog_redacts_workstation_paths_and_private_adapter_config(self) -> None:
        result = self.gateway.execute(
            "projects.list",
            {},
            context=self.context,
            grant=self.grant("projects.list", projects=()),
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
            context=self.context,
            grant=self.grant("project.inventory"),
        )

        self.assertTrue(result.ok)
        self.assertNotIn("project_root", result.data)
        self.assertEqual(result.data["entries"][0]["path"], "docs/README.md")

    def test_git_results_redact_absolute_command(self) -> None:
        result = self.gateway.execute(
            "git.status",
            {"project": "scene"},
            context=self.context,
            grant=self.grant("git.status"),
        )

        self.assertTrue(result.ok)
        self.assertNotIn("command", result.data)

    def test_artifact_preview_redacts_local_absolute_path(self) -> None:
        result = self.gateway.execute(
            "artifact.preview",
            {"project": "scene", "artifact_name": "preview.png"},
            context=self.context,
            grant=self.grant("artifact.preview"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.data["artifact_name"], "preview.png")
        self.assertNotIn("path", result.data)


if __name__ == "__main__":
    unittest.main()
