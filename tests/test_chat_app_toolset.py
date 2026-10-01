from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ordax_chat_app.policy import CapabilityPolicyStore
from ordax_chat_app.toolset import DEVELOPMENT_TOOLS, DevelopmentToolset
from ordax_core import OrchestratorStore
from ordax_dev_agent.models import ActionResult


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def execute(self, action, payload):
        self.calls.append((action, payload))
        if action == "workspace.text_read":
            return ActionResult(
                True,
                "read",
                {
                    "relative_path": payload["path"],
                    "sha256": "abc",
                    "content": "hello",
                },
            )
        return ActionResult(True, "ok", {"action": action})


class DevelopmentToolsetTests(unittest.TestCase):
    def test_initial_toolbox_is_small_strict_and_project_is_not_model_controlled(self):
        def assert_strict_object(schema):
            if not isinstance(schema, dict):
                return
            if schema.get("type") == "object":
                self.assertFalse(schema.get("additionalProperties", True))
                properties = schema.get("properties", {})
                self.assertEqual(set(properties), set(schema.get("required", [])))
                for child in properties.values():
                    assert_strict_object(child)
            if schema.get("type") == "array":
                assert_strict_object(schema.get("items"))
            for option in schema.get("anyOf", []):
                assert_strict_object(option)

        self.assertLessEqual(len(DEVELOPMENT_TOOLS), 24)
        names = {item["name"] for item in DEVELOPMENT_TOOLS}
        self.assertIn("terminal", names)
        self.assertIn("git", names)
        self.assertIn("workspace_patch", names)
        self.assertIn("agents", names)
        for tool in DEVELOPMENT_TOOLS:
            self.assertTrue(tool["strict"])
            parameters = tool["parameters"]
            self.assertNotIn("project", parameters["properties"])
            assert_strict_object(parameters)

    def test_executor_injects_selected_project_and_removes_null_optionals(self):
        registry = FakeRegistry()
        toolset = DevelopmentToolset(registry, project="acheguese")
        output = json.loads(
            toolset.execute(
                "workspace_read",
                json.dumps(
                    {
                        "path": "src/app.ts",
                        "start_line": 1,
                        "end_line": None,
                    }
                ),
            )
        )
        self.assertTrue(output["ok"])
        self.assertEqual(registry.calls[0][0], "workspace.text_read")
        self.assertEqual(
            registry.calls[0][1],
            {
                "project": "acheguese",
                "path": "src/app.ts",
                "start_line": 1,
            },
        )


    def test_terminal_env_is_converted_from_strict_pairs(self):
        registry = FakeRegistry()
        toolset = DevelopmentToolset(registry, project="demo")
        output = json.loads(
            toolset.execute(
                "terminal",
                json.dumps(
                    {
                        "cwd": ".",
                        "argv": ["python", "-V"],
                        "command": None,
                        "shell": False,
                        "timeout_seconds": 30,
                        "env": [
                            {"name": "MODE", "value": "test"},
                            {"name": "CI", "value": "1"},
                        ],
                    }
                ),
            )
        )
        self.assertTrue(output["ok"])
        self.assertEqual(registry.calls[0][0], "terminal.exec")
        self.assertEqual(
            registry.calls[0][1]["env"],
            {"MODE": "test", "CI": "1"},
        )


    def test_browser_tool_routes_operation_without_exposing_project(self):
        registry = FakeRegistry()
        toolset = DevelopmentToolset(registry, project="demo")
        output = json.loads(
            toolset.execute(
                "browser",
                json.dumps(
                    {
                        "operation": "snapshot",
                        "session_id": "session-1",
                        "url": None,
                        "headless": None,
                        "wait_seconds": None,
                        "node_id": None,
                        "text": None,
                        "clear": None,
                        "max_elements": 120,
                        "width": None,
                        "height": None,
                    }
                ),
            )
        )
        self.assertTrue(output["ok"])
        self.assertEqual(registry.calls[0][0], "browser.snapshot")
        self.assertEqual(
            registry.calls[0][1],
            {"project": "demo", "session_id": "session-1", "max_elements": 120},
        )

    def test_computer_tool_is_hidden_until_project_grant(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = CapabilityPolicyStore(Path(directory) / "state.db")
            toolset = DevelopmentToolset(
                FakeRegistry(),
                project="demo",
                policy=policy,
            )
            self.assertNotIn("computer", {item["name"] for item in toolset.definitions})

            policy.set("demo", "computer.observe", True)
            visible = next(item for item in toolset.definitions if item["name"] == "computer")
            operations = visible["parameters"]["properties"]["operation"]["enum"]
            self.assertEqual(operations, ["windows", "active_window", "screenshot"])

    def test_computer_observe_cannot_authorize_interaction(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = CapabilityPolicyStore(Path(directory) / "state.db")
            policy.set("demo", "computer.observe", True)
            registry = FakeRegistry()
            toolset = DevelopmentToolset(registry, project="demo", policy=policy)

            denied = json.loads(
                toolset.execute(
                    "computer",
                    json.dumps(
                        {
                            "operation": "click",
                            "mode": None,
                            "max_items": None,
                            "handle": None,
                            "x": 10,
                            "y": 20,
                            "button": "left",
                            "clicks": 1,
                            "text": None,
                            "keys": None,
                            "amount": None,
                            "horizontal": None,
                        }
                    ),
                )
            )
            self.assertFalse(denied["ok"])
            self.assertIn("computer.interact", denied["summary"])
            self.assertEqual(registry.calls, [])

            observed = json.loads(
                toolset.execute(
                    "computer",
                    json.dumps(
                        {
                            "operation": "screenshot",
                            "mode": "desktop",
                            "max_items": None,
                            "handle": None,
                            "x": None,
                            "y": None,
                            "button": None,
                            "clicks": None,
                            "text": None,
                            "keys": None,
                            "amount": None,
                            "horizontal": None,
                        }
                    ),
                )
            )
            self.assertTrue(observed["ok"])
            self.assertEqual(registry.calls[0][0], "computer.screenshot")
            self.assertEqual(
                registry.calls[0][1],
                {"project": "demo", "mode": "desktop"},
            )

    def test_prime_can_create_and_delegate_to_worker_through_single_agents_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            store = OrchestratorStore(Path(directory) / "state.db")
            prime = store.create_agent("demo", "Prime", "chat coordinator")
            toolset = DevelopmentToolset(
                FakeRegistry(),
                project="demo",
                orchestrator=store,
                agent_id=prime["id"],
            )
            created = json.loads(
                toolset.execute(
                    "agents",
                    json.dumps(
                        {
                            "operation": "create_worker",
                            "worker_id": None,
                            "name": "QA",
                            "role": "quality worker",
                            "title": None,
                            "instruction": None,
                            "priority": None,
                            "message": None,
                            "unread_only": None,
                        }
                    ),
                )
            )
            self.assertTrue(created["ok"])
            worker_id = created["data"]["id"]

            delegated = json.loads(
                toolset.execute(
                    "agents",
                    json.dumps(
                        {
                            "operation": "delegate",
                            "worker_id": worker_id,
                            "name": None,
                            "role": None,
                            "title": "Run regression tests",
                            "instruction": "Run the suite and report failures.",
                            "priority": 90,
                            "message": None,
                            "unread_only": None,
                        }
                    ),
                )
            )
            self.assertTrue(delegated["ok"])
            queued = store.list_work("demo", agent_id=worker_id, states=["queued"])
            self.assertEqual(len(queued), 1)
            self.assertEqual(queued[0]["title"], "Run regression tests")

    def test_worker_cannot_spawn_or_delegate_to_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            store = OrchestratorStore(Path(directory) / "state.db")
            prime = store.create_agent("demo", "Prime", "chat coordinator")
            worker = store.create_agent("demo", "Backend", "backend worker", parent_agent_id=prime["id"])
            sibling = store.create_agent("demo", "QA", "quality worker", parent_agent_id=prime["id"])
            toolset = DevelopmentToolset(
                FakeRegistry(),
                project="demo",
                orchestrator=store,
                agent_id=worker["id"],
            )
            delegated = json.loads(
                toolset.execute(
                    "agents",
                    json.dumps(
                        {
                            "operation": "delegate",
                            "worker_id": sibling["id"],
                            "name": None,
                            "role": None,
                            "title": "Do work",
                            "instruction": "Run tests",
                            "priority": 50,
                            "message": None,
                            "unread_only": None,
                        }
                    ),
                )
            )
            self.assertFalse(delegated["ok"])
            self.assertIn("only a coordinator", delegated["summary"])

    def test_model_cannot_smuggle_project_field(self):
        registry = FakeRegistry()
        toolset = DevelopmentToolset(registry, project="allowed")
        output = json.loads(
            toolset.execute(
                "workspace_list",
                json.dumps(
                    {
                        "path": ".",
                        "max_depth": 1,
                        "max_entries": 10,
                        "include_hidden": False,
                        "project": "other",
                    }
                ),
            )
        )
        self.assertFalse(output["ok"])
        self.assertIn("unsupported tool argument", output["summary"])
        self.assertEqual(registry.calls, [])


if __name__ == "__main__":
    unittest.main()
