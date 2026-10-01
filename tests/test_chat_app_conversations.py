from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ordax_chat_app.conversations import ConversationStore


class ConversationStoreTests(unittest.TestCase):
    def test_threads_items_and_visible_messages_survive_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "state.db"
            store = ConversationStore(db)
            thread = store.create_thread(
                project_slug="demo",
                agent_id="agent-1",
                session_id="session-1",
                provider="openai-chatgpt-plan",
                model="gpt-test",
            )
            store.append_items(
                thread["id"],
                [
                    {"role": "user", "content": "hello"},
                    {"type": "reasoning", "id": "r1", "encrypted_content": "opaque"},
                ],
            )
            store.append_message(thread["id"], "user", "hello")
            store.append_message(thread["id"], "assistant", "hi")
            store.set_title(thread["id"], "Demo chat")

            reopened = ConversationStore(db)
            loaded = reopened.thread(thread["id"])
            self.assertEqual(loaded["title"], "Demo chat")
            self.assertEqual(len(reopened.items(thread["id"])), 2)
            self.assertEqual(
                [item["role"] for item in reopened.messages(thread["id"])],
                ["user", "assistant"],
            )

            reopened.replace_items(
                thread["id"],
                [{"role": "user", "content": "[checkpoint]"}],
            )
            reopened.update_session(thread["id"], "session-2")
            self.assertEqual(reopened.items(thread["id"]), [{"role": "user", "content": "[checkpoint]"}])
            self.assertEqual(reopened.thread(thread["id"])["session_id"], "session-2")
            self.assertEqual(len(reopened.messages(thread["id"])), 2)


if __name__ == "__main__":
    unittest.main()
