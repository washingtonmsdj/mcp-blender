from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from ordax_chat_app.autonomy_service import AutonomyService


class FakeRuntime:
    pass


class FakeSupervisor:
    calls = 0

    def __init__(self, runtime, *, model, context_window_tokens, project_slugs=None):
        self.runtime = runtime
        self.model = model
        self.context_window_tokens = context_window_tokens
        self.project_slugs = project_slugs

    def run_cycle(self):
        type(self).calls += 1
        return []


class AutonomyServiceTests(unittest.TestCase):
    def test_start_is_idempotent_and_stop_is_clean(self):
        FakeSupervisor.calls = 0
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = AutonomyService(FakeRuntime())
            started = service.start(model="gpt-test", project_slugs=["demo"], idle_sleep_seconds=0.5)
            self.assertTrue(started["running"])
            again = service.start(model="gpt-test", project_slugs=["demo"], idle_sleep_seconds=0.5)
            self.assertTrue(again["running"])
            self.assertEqual(again["model"], "gpt-test")

            deadline = time.time() + 2
            while FakeSupervisor.calls == 0 and time.time() < deadline:
                time.sleep(0.01)
            self.assertGreater(FakeSupervisor.calls, 0)

            stopped = service.stop(timeout_seconds=2)
            self.assertFalse(stopped["running"])
            self.assertFalse(stopped["thread_alive"])

    def test_project_scope_change_requires_restart(self):
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = AutonomyService(FakeRuntime())
            service.start(model="gpt-a", project_slugs=["demo"], idle_sleep_seconds=0.5)
            try:
                status = service.status()
                self.assertEqual(status["project_slugs"], ("demo",))
                with self.assertRaisesRegex(RuntimeError, "different model or project scope"):
                    service.start(model="gpt-a", project_slugs=["other"], idle_sleep_seconds=0.5)
            finally:
                service.stop(timeout_seconds=2)

    def test_running_model_cannot_change_without_stop(self):
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = AutonomyService(FakeRuntime())
            service.start(model="gpt-a", project_slugs=["demo"], idle_sleep_seconds=0.5)
            try:
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    service.start(model="gpt-b", project_slugs=["demo"], idle_sleep_seconds=0.5)
            finally:
                service.stop(timeout_seconds=2)


if __name__ == "__main__":
    unittest.main()
