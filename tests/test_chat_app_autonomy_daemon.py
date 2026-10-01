from __future__ import annotations

import threading
import unittest

from ordax_chat_app.autonomy_daemon import AutonomyDaemon


class FakePreferences:
    def __init__(self, payload):
        self.payload = dict(payload)

    def load(self):
        return dict(self.payload)


class FakeService:
    def __init__(self, payload):
        self.preferences = FakePreferences(payload)
        self._status = {
            "running": False,
            "model": None,
            "project_slugs": (),
            "external_running": False,
        }
        self.resume_calls = 0
        self.stop_calls = 0

    def status(self):
        return dict(self._status)

    def resume_persisted(self):
        self.resume_calls += 1
        cfg = self.preferences.load()
        self._status = {
            "running": bool(cfg.get("enabled")),
            "model": cfg.get("model"),
            "project_slugs": tuple(cfg.get("project_slugs") or ()),
            "external_running": False,
        }
        return self.status()

    def stop(self, *, timeout_seconds=10.0, disable_persisted=True):
        self.stop_calls += 1
        self._status["running"] = False
        return self.status()


class AutonomyDaemonTests(unittest.TestCase):
    def test_enabled_config_is_resumed_once_and_kept_running(self):
        service = FakeService({
            "enabled": True,
            "model": "gpt-test",
            "project_slugs": ["demo"],
        })
        daemon = AutonomyDaemon(runtime=object(), service=service)
        first = daemon.sync_once()
        self.assertTrue(first["running"])
        self.assertEqual(service.resume_calls, 1)

        second = daemon.sync_once()
        self.assertTrue(second["running"])
        self.assertEqual(service.resume_calls, 1)

    def test_config_change_restarts_without_disabling_persisted_flag(self):
        service = FakeService({
            "enabled": True,
            "model": "gpt-a",
            "project_slugs": ["demo"],
        })
        daemon = AutonomyDaemon(runtime=object(), service=service)
        daemon.sync_once()
        service.preferences.payload["model"] = "gpt-b"
        status = daemon.sync_once()
        self.assertTrue(status["running"])
        self.assertEqual(status["model"], "gpt-b")
        self.assertEqual(service.stop_calls, 1)
        self.assertEqual(service.resume_calls, 2)

    def test_disabled_config_stops_local_supervisor(self):
        service = FakeService({
            "enabled": True,
            "model": "gpt-a",
            "project_slugs": ["demo"],
        })
        daemon = AutonomyDaemon(runtime=object(), service=service)
        daemon.sync_once()
        service.preferences.payload["enabled"] = False
        status = daemon.sync_once()
        self.assertFalse(status["running"])
        self.assertEqual(service.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
