from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_chat_app.autonomy import AutonomousAgentRunner, AutonomySupervisor
from ordax_chat_app.conversations import ConversationStore
from ordax_chat_app.providers.base import ChatModel, ChatTurnResult
from ordax_chat_app.runtime import OrdaxChatRuntime
from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def list_models(self):
        return [ChatModel("gpt-test", "GPT Test")]

    def run_turn(self, *, model, input_items, instructions=None, tools=None, on_delta=None):
        self.calls += 1
        return ChatTurnResult(
            text="Autonomous task completed and tests are green.",
            response_id=f"resp-{self.calls}",
            usage={"input_tokens": 1000, "output_tokens": 120},
            output_items=[
                {
                    "type": "message",
                    "id": f"msg-{self.calls}",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Autonomous task completed and tests are green.",
                        }
                    ],
                }
            ],
        )


class AutonomousAgentRunnerTests(unittest.TestCase):
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

        registry = ActionRegistry(
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
            agent=registry,
            conversations=ConversationStore(self.db),
            provider_factory=lambda: self.provider,
        )
        self.prime = self.runtime.orchestrator.create_agent(
            "demo", "Prime", "chat coordinator"
        )
        self.worker = self.runtime.orchestrator.create_agent(
            "demo",
            "Backend",
            "backend worker",
            parent_agent_id=self.prime["id"],
        )

    def test_worker_claims_executes_completes_and_reports_to_prime(self):
        work = self.runtime.orchestrator.enqueue_work(
            self.worker["id"],
            "Fix backend",
            "Inspect the backend, fix the bug and run the tests.",
            priority=80,
        )
        runner = AutonomousAgentRunner(
            self.runtime,
            agent_id=self.worker["id"],
            model="gpt-test",
            context_window_tokens=10000,
            runner_id="runner-1",
        )
        result = runner.run_once()

        self.assertEqual(result.state, "done")
        self.assertEqual(result.work_id, work["id"])
        self.assertIsNotNone(result.thread_id)
        self.assertEqual(self.provider.calls, 1)

        queued = self.runtime.orchestrator.list_work("demo")
        item = next(item for item in queued if item["id"] == work["id"])
        self.assertEqual(item["state"], "done")
        self.assertIn("tests are green", item["result"])

        inbox = self.runtime.orchestrator.inbox(self.prime["id"])
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]["correlation_id"], work["id"])
        self.assertIn("tests are green", inbox[0]["content"])

        messages = self.runtime.messages(result.thread_id)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])

    def test_supervisor_turns_worker_report_into_durable_prime_followup(self):
        work = self.runtime.orchestrator.enqueue_work(
            self.worker["id"],
            "Fix backend",
            "Inspect the backend and report the result.",
            priority=80,
        )
        supervisor = AutonomySupervisor(
            self.runtime,
            model="gpt-test",
            context_window_tokens=10000,
            runner_prefix="supervisor-test",
            project_slugs={"demo"},
        )
        first = supervisor.run_cycle()
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].work_id, work["id"])

        self.assertEqual(self.runtime.orchestrator.inbox(self.prime["id"]), [])
        prime_work = self.runtime.orchestrator.list_work(
            "demo",
            agent_id=self.prime["id"],
            states=["queued"],
        )
        self.assertEqual(len(prime_work), 1)
        self.assertEqual(prime_work[0]["title"], "Review worker results")
        self.assertIn("Backend", prime_work[0]["instruction"])
        self.assertIn("tests are green", prime_work[0]["instruction"])

        second = supervisor.run_cycle()
        prime_result = next(item for item in second if item.agent_id == self.prime["id"])
        self.assertEqual(prime_result.state, "done")
        final = self.runtime.orchestrator.list_work(
            "demo",
            agent_id=self.prime["id"],
        )
        reviewed = next(item for item in final if item["id"] == prime_work[0]["id"])
        self.assertEqual(reviewed["state"], "done")

    def test_supervisor_idle_cycle_does_not_call_provider(self):
        supervisor = AutonomySupervisor(
            self.runtime,
            model="gpt-test",
            context_window_tokens=10000,
            runner_prefix="supervisor-test",
        )
        results = supervisor.run_cycle()
        self.assertEqual(results, [])
        self.assertEqual(self.provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
