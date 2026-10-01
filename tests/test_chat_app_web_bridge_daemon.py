from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ordax_chat_app.web_bridge_daemon import WebBridgeDaemon


class FakeManager:
    def __init__(self, *, configured=True, enabled=True, running=False, fail_start=False):
        self.configured = configured
        self.enabled = enabled
        self.running = running
        self.fail_start = fail_start
        self.start_calls = 0
        self.stop_calls = 0

    def status(self):
        return {
            "configured": self.configured,
            "enabled": self.enabled,
            "running": self.running,
            "tunnel_id": "tunnel_test" if self.configured else None,
            "profile": "ordax-dev",
            "pid": 4242 if self.running else None,
        }

    def start(self, *, persist_enabled=True):
        self.start_calls += 1
        if self.fail_start:
            raise RuntimeError("tunnel unavailable")
        if persist_enabled:
            self.enabled = True
        self.running = True
        return self.status()

    def stop(self, *, persist_disabled=True):
        self.stop_calls += 1
        self.running = False
        if persist_disabled:
            self.enabled = False
        return self.status()


class WebBridgeDaemonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "daemon.json"

    def daemon(self, manager):
        return WebBridgeDaemon(manager, state_path=self.state)

    def test_unconfigured_bridge_idles_without_starting(self):
        manager = FakeManager(configured=False, enabled=False)
        state = self.daemon(manager).sync_once()
        self.assertEqual(state["state"], "unconfigured")
        self.assertEqual(manager.start_calls, 0)

    def test_disabled_bridge_stays_off_and_stops_stray_runtime(self):
        manager = FakeManager(configured=True, enabled=False, running=True)
        state = self.daemon(manager).sync_once()
        self.assertEqual(state["state"], "disabled")
        self.assertFalse(state["running"])
        self.assertEqual(manager.start_calls, 0)
        self.assertEqual(manager.stop_calls, 1)
        self.assertFalse(manager.enabled)

    def test_enabled_bridge_starts_without_mutating_persisted_intent(self):
        manager = FakeManager(configured=True, enabled=True, running=False)
        state = self.daemon(manager).sync_once()
        self.assertEqual(state["state"], "healthy")
        self.assertTrue(state["running"])
        self.assertEqual(manager.start_calls, 1)
        self.assertTrue(manager.enabled)

    def test_healthy_bridge_is_not_started_twice(self):
        manager = FakeManager(configured=True, enabled=True, running=True)
        state = self.daemon(manager).sync_once()
        self.assertEqual(state["state"], "healthy")
        self.assertEqual(manager.start_calls, 0)

    def test_start_failure_records_bounded_retry_and_no_secret(self):
        manager = FakeManager(configured=True, enabled=True, running=False, fail_start=True)
        state = self.daemon(manager).sync_once()
        self.assertEqual(state["state"], "degraded")
        self.assertGreaterEqual(state["retry_seconds"], 5)
        self.assertIn("tunnel unavailable", state["last_error"])
        payload = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertNotIn("api_key", payload)
        self.assertEqual(payload["failures"], 1)


if __name__ == "__main__":
    unittest.main()
