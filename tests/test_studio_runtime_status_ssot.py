from __future__ import annotations

import unittest

from ordax_studio.web_desktop import _device_agent_health


class StudioRuntimeStatusSsotTests(unittest.TestCase):
    def test_live_ready_runtime_is_authoritative_without_legacy_task(self):
        status = _device_agent_health(
            {"state": "ready", "paired": True, "transport_state": "connected"},
            {"exists": False, "state": "Missing"},
            {},
            configured=True,
            resilience_ok=True,
            resilience_summary="legacy healthy",
        )
        self.assertTrue(status["ok"])
        self.assertEqual("runtime-status", status["health_source"])
        self.assertTrue(status["runtime_reachable"])
        self.assertEqual("ready", status["runtime_state"])
        self.assertEqual("connected", status["transport_state"])
        self.assertFalse(status["scheduled_task_exists"])

    def test_live_runtime_error_is_not_hidden_by_legacy_supervisor(self):
        status = _device_agent_health(
            {"state": "control-plane-error", "paired": True, "transport_state": "reconnecting"},
            {"exists": True, "state": "Running"},
            {"ok": True},
            configured=True,
            resilience_ok=True,
            resilience_summary="legacy healthy",
        )
        self.assertFalse(status["ok"])
        self.assertEqual("runtime-status", status["health_source"])
        self.assertEqual("control-plane-error", status["runtime_state"])
        self.assertEqual("reconnecting", status["transport_state"])
        self.assertIn("degradado", status["summary"])

    def test_legacy_supervisor_is_only_a_fallback_when_runtime_is_absent(self):
        status = _device_agent_health(
            {},
            {"exists": True, "state": "Running"},
            {"ok": True},
            configured=True,
            resilience_ok=True,
            resilience_summary="legacy healthy",
        )
        self.assertTrue(status["ok"])
        self.assertEqual("legacy-resilience", status["health_source"])
        self.assertFalse(status["runtime_reachable"])

    def test_no_runtime_and_no_legacy_supervisor_is_offline(self):
        status = _device_agent_health(
            {},
            {"exists": False, "state": "Missing"},
            {},
            configured=True,
            resilience_ok=False,
            resilience_summary="resilience unavailable",
        )
        self.assertFalse(status["ok"])
        self.assertEqual("none", status["health_source"])
        self.assertEqual("resilience unavailable", status["summary"])


if __name__ == "__main__":
    unittest.main()
