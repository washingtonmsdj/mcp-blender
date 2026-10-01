from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ordax_chat_app import WorkOutcome, WorkerLoop
from ordax_core import OrchestratorStore


class WorkerLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = OrchestratorStore(self.root / "state.db")
        self.agent = self.store.create_agent("demo", "Worker", "implementation")

    def test_idle_never_calls_model_handler(self) -> None:
        calls = []

        def handler(work):
            calls.append(work)
            return WorkOutcome(ok=True)

        loop = WorkerLoop(
            self.store,
            agent_id=self.agent["id"],
            runner_id="runner-1",
            handler=handler,
            lease_seconds=60,
        )
        result = loop.run_once()
        self.assertEqual(result["state"], "idle")
        self.assertEqual(calls, [])

    def test_work_is_completed_from_handler_outcome(self) -> None:
        work = self.store.enqueue_work(
            self.agent["id"], "Implement", "Change the code"
        )

        def handler(item):
            self.assertEqual(item["id"], work["id"])
            return WorkOutcome(ok=True, result="tests green")

        loop = WorkerLoop(
            self.store,
            agent_id=self.agent["id"],
            runner_id="runner-1",
            handler=handler,
            lease_seconds=60,
        )
        result = loop.run_once()
        self.assertEqual(result["state"], "done")
        self.assertEqual(result["work"]["result"], "tests green")

    def test_handler_exception_requeues_work(self) -> None:
        self.store.enqueue_work(
            self.agent["id"], "Implement", "Crash once", max_attempts=2
        )

        def handler(_item):
            raise RuntimeError("provider disconnected")

        loop = WorkerLoop(
            self.store,
            agent_id=self.agent["id"],
            runner_id="runner-1",
            handler=handler,
            lease_seconds=60,
        )
        result = loop.run_once()
        self.assertEqual(result["state"], "queued")
        self.assertTrue(result["handler_exception"])
        queued = self.store.list_work("demo", states=["queued"])
        self.assertEqual(len(queued), 1)
        self.assertIn("provider disconnected", queued[0]["error"])


if __name__ == "__main__":
    unittest.main()
