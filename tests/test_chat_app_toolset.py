from __future__ import annotations

import json
import unittest

from ordax_chat_app.toolset import DEVELOPMENT_TOOLS, DevelopmentToolset
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

        self.assertLessEqual(len(DEVELOPMENT_TOOLS), 20)
        names = {item["name"] for item in DEVELOPMENT_TOOLS}
        self.assertIn("terminal", names)
        self.assertIn("git", names)
        self.assertIn("workspace_patch", names)
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
