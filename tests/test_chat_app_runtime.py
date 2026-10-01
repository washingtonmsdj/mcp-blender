from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_chat_app.conversations import ConversationStore
from ordax_chat_app.providers.base import ChatModel, ChatTurnResult
from ordax_chat_app.runtime import OrdaxChatRuntime
from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


class FakeProvider:
    def __init__(self):
        self.calls = []

    def list_models(self):
        return [ChatModel("gpt-test", "GPT Test")]

    def run_turn(self, *, model, input_items, instructions=None, tools=None, on_delta=None):
        self.calls.append(
            {
                "model": model,
                "input_items": [dict(item) for item in input_items],
                "instructions": instructions,
                "tools": tools,
            }
        )
        if tools is None:
            return ChatTurnResult(
                text=(
                    "Objective: finish the selected project.\n"
                    "Completed: inspected current state.\n"
                    "Next: continue from tests."
                ),
                response_id="compact-1",
                usage={"input_tokens": 200, "output_tokens": 80},
                output_items=[
                    {
                        "type": "message",
                        "id": "compact-msg",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "checkpoint"}],
                    }
                ],
            )
        return ChatTurnResult(
            text="Implementation inspected and ready to continue.",
            response_id="resp-1",
            usage={"input_tokens": 7000, "output_tokens": 1200},
            output_items=[
                {
                    "type": "message",
                    "id": "msg-1",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Implementation inspected and ready to continue.",
                        }
                    ],
                }
            ],
        )


class OrdaxChatRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.db = self.root / "state.db"
        self.env = patch.dict(os.environ, {"ORDAX_MEMORY_DB": str(self.db)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.registry = ActionRegistry(
            AgentConfig(
                agent_name="test",
                poll_seconds=0.25,
                state_dir=self.root / "agent-state",
                agent_repo_path=self.root / "agent",
                hordax_path=self.root / "hordax",
                bridge_path=self.root / "bridge",
                projects={"demo": {"path": str(self.project), "apps": []}},
                default_project="demo",
            )
        )
        self.provider = FakeProvider()
        self.runtime = OrdaxChatRuntime(
            agent=self.registry,
            conversations=ConversationStore(self.db),
            provider_factory=lambda: self.provider,
        )

    def test_new_thread_and_compact_resume_are_automatic(self):
        thread = self.runtime.new_thread(
            project="demo",
            model="gpt-test",
            context_window_tokens=10000,
        )
        previous_session = thread["session_id"]

        result = self.runtime.send_message(
            thread["id"],
            "Continue developing the project",
        )
        self.assertTrue(result.session_rotated)
        self.assertIsNone(result.compaction_error)
        self.assertNotEqual(result.session_id, previous_session)
        self.assertEqual(result.text, "Implementation inspected and ready to continue.")

        old = self.runtime.orchestrator.session(previous_session)
        self.assertEqual(old["state"], "rotated")
        self.assertEqual(old["end_reason"], "context_rollover")

        updated = self.runtime.conversations.thread(thread["id"])
        self.assertEqual(updated["session_id"], result.session_id)
        model_items = self.runtime.conversations.items(thread["id"])
        self.assertEqual(len(model_items), 1)
        self.assertIn("ORDAX CONTINUATION CHECKPOINT", model_items[0]["content"])
        self.assertIn("continue from tests", model_items[0]["content"])

        visible = self.runtime.messages(thread["id"])
        self.assertEqual(
            [(item["role"], item["text"]) for item in visible],
            [
                ("user", "Continue developing the project"),
                ("assistant", "Implementation inspected and ready to continue."),
            ],
        )
        self.assertEqual(self.runtime.conversations.thread(thread["id"])["title"], "Continue developing the project")
        self.assertEqual(len(self.provider.calls), 2)
        self.assertIsNotNone(self.provider.calls[0]["tools"])
        self.assertIsNone(self.provider.calls[1]["tools"])

    def test_model_picker_uses_provider_catalog(self):
        self.assertEqual(
            self.runtime.models(),
            [{"id": "gpt-test", "display_name": "GPT Test"}],
        )


if __name__ == "__main__":
    unittest.main()
