from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ordax_chat_app.agent_engine import AgentChatEngine
from ordax_chat_app.providers.base import ChatTurnResult
from ordax_chat_app.toolset import DevelopmentToolset, ToolExecutionResult
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
                {"relative_path": payload["path"], "content": "value = 1", "sha256": "sha"},
            )
        return ActionResult(True, "ok", {})


class FakeProvider:
    def __init__(self):
        self.requests = []

    def run_turn(self, *, model, input_items, instructions=None, tools=None, on_delta=None):
        self.requests.append(
            {
                "model": model,
                "input_items": [dict(item) for item in input_items],
                "instructions": instructions,
                "tools": tools,
            }
        )
        if len(self.requests) == 1:
            return ChatTurnResult(
                text="",
                response_id="resp-1",
                usage={"input_tokens": 6000, "output_tokens": 1000},
                output_items=[
                    {"type": "reasoning", "id": "rs-1", "encrypted_content": "opaque"},
                    {
                        "type": "function_call",
                        "id": "fc-1",
                        "call_id": "call-1",
                        "name": "workspace_read",
                        "arguments": '{"path":"src/app.py","start_line":1,"end_line":null}',
                    },
                ],
            )
        return ChatTurnResult(
            text="Done.",
            response_id="resp-2",
            usage={"input_tokens": 1100, "output_tokens": 200},
            output_items=[
                {
                    "type": "message",
                    "id": "msg-1",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Done."}],
                }
            ],
        )




class VisualToolset:
    definitions = [{"type": "function", "name": "computer", "parameters": {"type": "object"}}]

    def execute_with_followups(self, name, arguments):
        self.last = (name, arguments)
        return ToolExecutionResult(
            output='{"ok":true,"summary":"screenshot captured","data":{"artifact_name":"screen.png"}}',
            followup_items=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Visual output"},
                        {"type": "input_image", "image_url": "data:image/png;base64,iVBORw0KGgo=", "detail": "auto"},
                    ],
                }
            ],
        )


class VisualProvider:
    def __init__(self):
        self.requests = []

    def run_turn(self, *, model, input_items, instructions=None, tools=None, on_delta=None):
        self.requests.append([dict(item) for item in input_items])
        if len(self.requests) == 1:
            return ChatTurnResult(
                text="",
                response_id="visual-1",
                output_items=[
                    {
                        "type": "function_call",
                        "id": "fc-visual",
                        "call_id": "call-visual",
                        "name": "computer",
                        "arguments": '{"operation":"screenshot"}',
                    }
                ],
            )
        return ChatTurnResult(
            text="I can see the screen.",
            response_id="visual-2",
            output_items=[
                {
                    "type": "message",
                    "id": "msg-visual",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "I can see the screen."}],
                }
            ],
        )


class AgentChatEngineTests(unittest.TestCase):
    def test_function_call_result_and_reasoning_are_replayed(self):
        registry = FakeRegistry()
        provider = FakeProvider()
        engine = AgentChatEngine(
            provider,
            DevelopmentToolset(registry, project="demo"),
        )
        result = engine.run_turn(model="gpt", user_text="Inspect the file")

        self.assertEqual(result.text, "Done.")
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(result.model_rounds, 2)
        self.assertEqual(result.response_ids, ["resp-1", "resp-2"])
        self.assertEqual(registry.calls[0][0], "workspace.text_read")

        second_input = provider.requests[1]["input_items"]
        self.assertEqual(second_input[1]["type"], "reasoning")
        self.assertEqual(second_input[2]["type"], "function_call")
        self.assertEqual(second_input[3]["type"], "function_call_output")
        self.assertEqual(second_input[3]["call_id"], "call-1")


    def test_visual_tool_image_is_sent_to_model_but_not_persisted(self):
        provider = VisualProvider()
        toolset = VisualToolset()
        engine = AgentChatEngine(provider, toolset)
        result = engine.run_turn(model="gpt", user_text="Look at the screen")

        self.assertEqual(result.text, "I can see the screen.")
        second_input = provider.requests[1]
        image_messages = [
            item for item in second_input
            if item.get("role") == "user"
            and isinstance(item.get("content"), list)
            and any(part.get("type") == "input_image" for part in item["content"])
        ]
        self.assertEqual(len(image_messages), 1)
        persisted_images = [
            item for item in result.items
            if item.get("role") == "user"
            and isinstance(item.get("content"), list)
            and any(part.get("type") == "input_image" for part in item["content"])
        ]
        self.assertEqual(persisted_images, [])

    def test_usage_marks_session_for_rollover_after_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            store = OrchestratorStore(Path(directory) / "state.db")
            agent = store.create_agent("demo", "Prime", "coordinator")
            session = store.start_session(
                agent["id"],
                goal_id=None,
                provider="openai",
                model="gpt",
                context_window_tokens=10000,
                rollover_ratio=0.80,
            )
            engine = AgentChatEngine(
                FakeProvider(),
                DevelopmentToolset(FakeRegistry(), project="demo"),
                orchestrator=store,
                session_id=session["id"],
            )
            result = engine.run_turn(model="gpt", user_text="Inspect")
            self.assertTrue(result.rollover_recommended)
            current = store.session(session["id"])
            self.assertEqual(current["estimated_tokens"], 8300)
            self.assertTrue(current["should_rollover"])


if __name__ == "__main__":
    unittest.main()
