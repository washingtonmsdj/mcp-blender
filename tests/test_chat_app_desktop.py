from __future__ import annotations

import types
import unittest

from ordax_chat_app.desktop import DesktopApi
from ordax_chat_app.runtime import RuntimeChatResult


class FakeConversations:
    def thread(self, thread_id):
        return {
            "id": thread_id,
            "title": "Thread",
            "project_slug": "demo",
            "model": "gpt-test",
        }


class FakeOrchestrator:
    def status(self, project):
        return {
            "project": project,
            "agents": [],
            "goals": [],
            "active_sessions": [],
            "unread_messages": 0,
            "work_counts": {},
        }


class FakeRuntime:
    def __init__(self):
        self.agent = types.SimpleNamespace(
            config=types.SimpleNamespace(default_project="demo")
        )
        self.conversations = FakeConversations()
        self.orchestrator = FakeOrchestrator()

    def account_status(self):
        return {"connected": True, "account": {"name": "User", "email": "u@example.com"}}

    def projects(self):
        return [{"slug": "demo"}, {"slug": "other"}]

    def models(self):
        return [{"id": "gpt-test", "display_name": "GPT Test"}]

    def threads(self, project=None):
        return [{"id": "thread-1", "title": f"{project or 'all'} thread"}]

    def connect_chatgpt(self):
        return {"key": "account-1", "name": "User", "email": "u@example.com"}

    def new_thread(self, *, project, model):
        return {"id": "thread-2", "project_slug": project, "model": model}

    def messages(self, thread_id):
        return [{"role": "assistant", "text": f"opened {thread_id}"}]

    def send_message(self, thread_id, text):
        return RuntimeChatResult(
            thread_id=thread_id,
            text=f"reply to {text}",
            tool_calls=2,
            model_rounds=2,
            session_rotated=False,
            session_id="session-1",
        )


class DesktopApiTests(unittest.TestCase):
    def setUp(self):
        self.api = DesktopApi(FakeRuntime())

    def test_bootstrap_exposes_account_projects_models_and_threads(self):
        result = self.api.bootstrap()
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["default_project"], "demo")
        self.assertEqual(data["models"][0]["id"], "gpt-test")
        self.assertEqual(data["threads"][0]["id"], "thread-1")
        self.assertTrue(data["account"]["connected"])

    def test_create_open_and_send_thread(self):
        created = self.api.create_thread("demo", "gpt-test")
        self.assertTrue(created["ok"])
        self.assertEqual(created["data"]["id"], "thread-2")

        opened = self.api.open_thread("thread-1")
        self.assertTrue(opened["ok"])
        self.assertEqual(opened["data"]["messages"][0]["text"], "opened thread-1")

        sent = self.api.send_message("thread-1", "continue")
        self.assertTrue(sent["ok"])
        self.assertEqual(sent["data"]["tool_calls"], 2)
        self.assertEqual(sent["data"]["text"], "reply to continue")

    def test_orchestrator_status_is_project_scoped(self):
        status = self.api.orchestrator_status("demo")
        self.assertTrue(status["ok"])
        self.assertEqual(status["data"]["project"], "demo")


if __name__ == "__main__":
    unittest.main()
