from __future__ import annotations

import types
import unittest
from unittest.mock import patch

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
    def __init__(self):
        self.agents = {}
        self.work = []

    def status(self, project):
        return {
            "project": project,
            "agents": list(self.agents.values()),
            "goals": [],
            "active_sessions": [],
            "unread_messages": 0,
            "work_counts": {"queued": len(self.work)},
        }

    def create_agent(self, project, name, role, parent_agent_id=None):
        agent = {
            "id": f"agent-{len(self.agents)+1}",
            "project_slug": project,
            "name": name,
            "role": role,
            "parent_agent_id": parent_agent_id,
            "state": "active",
        }
        self.agents[agent["id"]] = agent
        return agent

    def get_agent(self, agent_id):
        return self.agents[agent_id]

    def set_agent_state(self, agent_id, state):
        self.agents[agent_id]["state"] = state
        return self.agents[agent_id]

    def enqueue_work(self, agent_id, title, instruction, priority=50):
        item = {
            "id": f"work-{len(self.work)+1}",
            "assigned_agent_id": agent_id,
            "title": title,
            "instruction": instruction,
            "priority": priority,
            "state": "queued",
        }
        self.work.append(item)
        return item



class FakePolicy:
    def __init__(self):
        self.values = {}

    def project(self, project):
        return {
            "computer.observe": self.values.get((project, "computer.observe"), False),
            "computer.interact": self.values.get((project, "computer.interact"), False),
        }

    def set(self, project, capability, enabled):
        self.values[(project, capability)] = bool(enabled)
        return {
            "project_slug": project,
            "capability": capability,
            "enabled": bool(enabled),
        }


class FakeAutonomy:
    def __init__(self):
        self.running = False
        self.resume_calls = 0

    def status(self):
        return {
            "running": self.running,
            "thread_alive": self.running,
            "persisted_enabled": False,
        }

    def resume_persisted(self):
        self.resume_calls += 1
        return self.status()

    def start(self, *, model, project_slugs):
        self.running = True
        return {
            **self.status(),
            "model": model,
            "project_slugs": tuple(project_slugs),
        }

    def stop(self, *, timeout_seconds=10.0, disable_persisted=True):
        self.running = False
        return self.status()

class FakeRuntime:
    def __init__(self):
        self.agent = types.SimpleNamespace(
            config=types.SimpleNamespace(default_project="demo"),
            select_available_project=lambda project: project if project in {"demo", "other"} else (_ for _ in ()).throw(ValueError("project not registered")),
        )
        self.conversations = FakeConversations()
        self.orchestrator = FakeOrchestrator()
        self.policy = FakePolicy()

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
        self.autonomy = FakeAutonomy()
        self.api = DesktopApi(
            FakeRuntime(),
            autonomy=self.autonomy,
            auto_resume=False,
        )

    def test_bootstrap_exposes_account_projects_models_and_threads(self):
        result = self.api.bootstrap()
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["default_project"], "demo")
        self.assertEqual(data["models"][0]["id"], "gpt-test")
        self.assertEqual(data["threads"][0]["id"], "thread-1")
        self.assertTrue(data["account"]["connected"])
        self.assertEqual(data["chat_modes"]["default"], "normal")
        self.assertFalse(data["chat_modes"]["normal"]["uses_work_codex_quota"])
        self.assertTrue(data["chat_modes"]["agent"]["uses_work_codex_quota"])
        self.assertTrue(data["chat_modes"]["normal"]["mcp_endpoint"].endswith("/mcp"))

    def test_normal_chat_info_and_open_use_regular_chat_path(self):
        info = self.api.normal_chat_info()
        self.assertEqual(info["mode"], "normal")
        self.assertFalse(info["uses_work_codex_quota"])
        self.assertTrue(info["mcp_endpoint"].endswith("/mcp"))

        with patch("ordax_chat_app.desktop.webbrowser.open", return_value=True) as opened:
            result = self.api.open_normal_chat()
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["opened"])
        opened.assert_called_once()

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

    def test_agent_creation_and_work_queue_are_project_scoped(self):
        created = self.api.orchestrator_agent_create(
            "demo", "Backend", "implementation worker", None
        )
        self.assertTrue(created["ok"])
        agent = created["data"]
        self.assertEqual(agent["project_slug"], "demo")

        queued = self.api.orchestrator_work_enqueue(
            "demo",
            agent["id"],
            "Fix backend",
            "Inspect and fix the backend, then run tests.",
            80,
        )
        self.assertTrue(queued["ok"])
        self.assertEqual(queued["data"]["assigned_agent_id"], agent["id"])
        self.assertEqual(queued["data"]["priority"], 80)

        wrong_project = self.api.orchestrator_work_enqueue(
            "other",
            agent["id"],
            "Wrong",
            "This must be rejected.",
            50,
        )
        self.assertFalse(wrong_project["ok"])
        self.assertIn("selected project", wrong_project["summary"])

    def test_computer_capability_grants_are_project_scoped(self):
        initial = self.api.capability_status("demo")
        self.assertTrue(initial["ok"])
        self.assertFalse(initial["data"]["computer.observe"])

        enabled = self.api.capability_set("demo", "computer.observe", True)
        self.assertTrue(enabled["ok"])
        self.assertTrue(enabled["data"]["capabilities"]["computer.observe"])

        other = self.api.capability_status("other")
        self.assertTrue(other["ok"])
        self.assertFalse(other["data"]["computer.observe"])

    def test_autonomy_status_starts_stopped(self):
        status = self.api.autonomy_status()
        self.assertTrue(status["ok"])
        self.assertFalse(status["data"]["running"])


if __name__ == "__main__":
    unittest.main()
