from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from ordax_chat_app.desktop import DesktopApi
from ordax_chat_app.runtime import RuntimeChatResult
from ordax_dev_agent.models import ActionResult


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

class FakeWebBridge:
    def __init__(self):
        self.running = False
        self.configured = False
        self.installed = False
        self.tunnel_id = None

    def status(self):
        return {
            "configured": self.configured,
            "tunnel_id": self.tunnel_id,
            "profile": "ordax-dev",
            "initialized": False,
            "client_installed": self.installed,
            "client_path": None,
            "running": self.running,
            "pid": 123 if self.running else None,
            "chatgpt_url": "https://chatgpt.com/",
            "tunnels_url": "https://platform.openai.com/settings/organization/tunnels",
            "api_keys_url": "https://platform.openai.com/settings/organization/api-keys",
        }

    def configure(self, tunnel_id, api_key):
        self.configured = True
        self.tunnel_id = tunnel_id
        return self.status()

    def install_client(self):
        self.installed = True
        return self.status()

    def start(self):
        if not self.configured:
            raise RuntimeError("not configured")
        self.running = True
        return self.status()

    def stop(self):
        self.running = False
        return self.status()

    def disconnect(self):
        self.running = False
        self.configured = False
        self.tunnel_id = None
        return self.status()

    @staticmethod
    def open_tunnels_page():
        return True

    @staticmethod
    def open_api_keys_page():
        return True


class FakeRuntime:
    def __init__(self):
        self.handoffs = {}
        self.agent = types.SimpleNamespace(
            config=types.SimpleNamespace(default_project="demo"),
            select_available_project=lambda project: project if project in {"demo", "other"} else (_ for _ in ()).throw(ValueError("project not registered")),
            execute=self._execute,
        )
        self.conversations = FakeConversations()
        self.orchestrator = FakeOrchestrator()
        self.policy = FakePolicy()

    def _execute(self, action, payload):
        if action == "handoff.create":
            handoff_id = "hof_0123456789abcdef0123456789abcdef"
            data = {
                "handoff_id": handoff_id,
                "project": payload["project"],
                "summary": payload["summary"],
                "next_action": payload.get("next_action", ""),
                "expires_at": "2099-01-01T00:00:00-03:00",
            }
            self.handoffs[handoff_id] = data
            return ActionResult(True, "created", data)
        if action == "handoff.get":
            data = self.handoffs.get(payload["handoff_id"])
            if data is None:
                return ActionResult(False, "not found", {})
            return ActionResult(True, "loaded", data)
        return ActionResult(False, f"unsupported: {action}", {})

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
        self.web_bridge = FakeWebBridge()
        self.api = DesktopApi(
            FakeRuntime(),
            autonomy=self.autonomy,
            web_bridge=self.web_bridge,
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

    def test_desktop_handoff_fallback_is_project_scoped(self):
        created = self.api.handoff_create(
            "demo",
            "Continue the project",
            "Run tests",
            24,
        )
        self.assertTrue(created["ok"])
        handoff_id = created["data"]["handoff_id"]
        self.assertTrue(handoff_id.startswith("hof_"))

        loaded = self.api.handoff_get("demo", handoff_id)
        self.assertTrue(loaded["ok"])
        self.assertEqual(loaded["data"]["summary"], "Continue the project")
        self.assertEqual(loaded["data"]["next_action"], "Run tests")

        wrong_project = self.api.handoff_get("unknown", handoff_id)
        self.assertFalse(wrong_project["ok"])

    def test_web_bridge_can_be_configured_installed_started_and_stopped(self):
        configured = self.api.web_bridge_configure(
            "tunnel_0123456789abcdef",
            "runtime-secret",
        )
        self.assertTrue(configured["ok"])
        self.assertTrue(configured["data"]["configured"])

        installed = self.api.web_bridge_install()
        self.assertTrue(installed["ok"])
        self.assertTrue(installed["data"]["client_installed"])

        started = self.api.web_bridge_start()
        self.assertTrue(started["ok"])
        self.assertTrue(started["data"]["running"])

        stopped = self.api.web_bridge_stop()
        self.assertTrue(stopped["ok"])
        self.assertFalse(stopped["data"]["running"])

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
