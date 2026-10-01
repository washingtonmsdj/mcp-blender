from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_chat_app.autonomy_preferences import AutonomyPreferencesStore
from ordax_chat_app.autonomy_service import AutonomyService
from ordax_chat_app.instance_lock import SingleInstanceLock


class FakeRuntime:
    def __init__(self, *, connected=True, projects=None):
        self.connected = connected
        self._projects = projects or [{"slug": "demo"}]

    def account_status(self):
        return {"connected": self.connected}

    def projects(self):
        return list(self._projects)


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
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.preferences = AutonomyPreferencesStore(Path(self.temp.name) / "autonomy.json")

    def service(self, runtime=None, *, lock_name="supervisor.lock"):
        return AutonomyService(
            runtime or FakeRuntime(),
            preferences=self.preferences,
            supervisor_lock=SingleInstanceLock(Path(self.temp.name) / lock_name),
        )

    def test_start_is_idempotent_and_stop_is_clean(self):
        FakeSupervisor.calls = 0
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = self.service()
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
            service = self.service()
            service.start(model="gpt-a", project_slugs=["demo"], idle_sleep_seconds=0.5)
            try:
                status = service.status()
                self.assertEqual(status["project_slugs"], ("demo",))
                with self.assertRaisesRegex(RuntimeError, "different model or project scope"):
                    service.start(model="gpt-a", project_slugs=["other"], idle_sleep_seconds=0.5)
            finally:
                service.stop(timeout_seconds=2)

    def test_start_persists_and_user_stop_disables_autonomy(self):
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = self.service()
            service.start(model="gpt-a", project_slugs=["demo"], idle_sleep_seconds=0.5)
            persisted = self.preferences.load()
            self.assertTrue(persisted["enabled"])
            self.assertEqual(persisted["model"], "gpt-a")
            self.assertEqual(persisted["project_slugs"], ["demo"])

            service.stop(timeout_seconds=2)
            self.assertFalse(self.preferences.load()["enabled"])

    def test_process_shutdown_can_preserve_persisted_autonomy(self):
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = self.service()
            service.start(model="gpt-a", project_slugs=["demo"], idle_sleep_seconds=0.5)
            service.stop(timeout_seconds=2, disable_persisted=False)
            self.assertTrue(self.preferences.load()["enabled"])

    def test_resume_persisted_restarts_only_when_account_and_project_are_available(self):
        self.preferences.save(
            enabled=True,
            model="gpt-a",
            project_slugs=["demo"],
            context_window_tokens=64000,
            idle_sleep_seconds=0.5,
        )
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = self.service(FakeRuntime(connected=True, projects=[{"slug": "demo"}]))
            status = service.resume_persisted()
            try:
                self.assertTrue(status["running"])
                self.assertEqual(status["model"], "gpt-a")
                self.assertEqual(status["project_slugs"], ("demo",))
                self.assertTrue(status["persisted_enabled"])
            finally:
                service.stop(timeout_seconds=2, disable_persisted=False)

            disconnected = self.service(FakeRuntime(connected=False, projects=[{"slug": "demo"}]))
            status = disconnected.resume_persisted()
            self.assertFalse(status["running"])
            self.assertIn("disconnected", status["last_error"])
            self.assertTrue(status["persisted_enabled"])

    def test_cross_process_lock_prevents_duplicate_supervisors(self):
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            first = self.service(lock_name="shared.lock")
            second = self.service(lock_name="shared.lock")
            first_status = first.start(
                model="gpt-a",
                project_slugs=["demo"],
                idle_sleep_seconds=0.5,
            )
            self.assertTrue(first_status["running"])
            try:
                second_status = second.start(
                    model="gpt-a",
                    project_slugs=["demo"],
                    idle_sleep_seconds=0.5,
                )
                self.assertFalse(second_status["running"])
                self.assertTrue(second_status["external_running"])
            finally:
                first.stop(timeout_seconds=2, disable_persisted=False)

            retried = second.start(
                model="gpt-a",
                project_slugs=["demo"],
                idle_sleep_seconds=0.5,
                persist=False,
            )
            try:
                self.assertTrue(retried["running"])
                self.assertFalse(retried["external_running"])
            finally:
                second.stop(timeout_seconds=2, disable_persisted=False)

    def test_running_model_cannot_change_without_stop(self):
        with patch("ordax_chat_app.autonomy_service.AutonomySupervisor", FakeSupervisor):
            service = self.service()
            service.start(model="gpt-a", project_slugs=["demo"], idle_sleep_seconds=0.5)
            try:
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    service.start(model="gpt-b", project_slugs=["demo"], idle_sleep_seconds=0.5)
            finally:
                service.stop(timeout_seconds=2)


if __name__ == "__main__":
    unittest.main()
