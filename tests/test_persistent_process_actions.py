from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


class PersistentProcessActionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.registry = ActionRegistry(
            AgentConfig(
                agent_name="test",
                poll_seconds=0.25,
                state_dir=self.root / "state",
                agent_repo_path=self.root / "agent",
                hordax_path=self.root / "hordax",
                bridge_path=self.root / "bridge",
                projects={"demo": {"path": str(self.project), "apps": []}},
                default_project="demo",
            )
        )
        self.process_id = None

    def tearDown(self):
        if self.process_id:
            try:
                self.registry.execute(
                    "process.stop",
                    {"project": "demo", "process_id": self.process_id},
                )
            except Exception:
                pass

    def test_start_status_logs_list_and_stop(self):
        started = self.registry.execute(
            "process.start",
            {
                "project": "demo",
                "cwd": ".",
                "argv": [
                    sys.executable,
                    "-u",
                    "-c",
                    "import time; print('ORDAX_PROCESS_READY', flush=True); time.sleep(30)",
                ],
                "env": {"ORDAX_TEST_VALUE": "1"},
                "wait_seconds": 1.5,
            },
        )
        self.assertTrue(started.ok, started.summary)
        self.process_id = started.data["process_id"]
        self.assertTrue(started.data["ownership_valid"])
        self.assertTrue(started.data["running"])

        status = self.registry.execute(
            "process.status",
            {"project": "demo", "process_id": self.process_id},
        )
        self.assertTrue(status.ok)
        self.assertTrue(status.data["running"])
        self.assertTrue(status.data["ownership_valid"])

        listing = self.registry.execute("process.list", {"project": "demo"})
        self.assertTrue(listing.ok)
        self.assertIn(
            self.process_id,
            [item["process_id"] for item in listing.data["processes"]],
        )

        tail = ""
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            logs = self.registry.execute(
                "process.logs",
                {
                    "project": "demo",
                    "process_id": self.process_id,
                    "max_bytes": 32768,
                },
            )
            self.assertTrue(logs.ok)
            tail = logs.data["tail"]
            if "ORDAX_PROCESS_READY" in tail:
                break
            time.sleep(0.1)
        self.assertIn("ORDAX_PROCESS_READY", tail)

        stopped = self.registry.execute(
            "process.stop",
            {"project": "demo", "process_id": self.process_id},
        )
        self.assertTrue(stopped.ok, stopped.summary)
        self.process_id = None

        status = self.registry.execute(
            "process.status",
            {"project": "demo", "process_id": started.data["process_id"]},
        )
        self.assertTrue(status.ok)
        self.assertFalse(status.data["running"])
        self.assertFalse(status.data["ownership_valid"])

    def test_write_stdin_reaches_managed_child(self):
        started = self.registry.execute(
            "process.start",
            {
                "project": "demo",
                "cwd": ".",
                "argv": [
                    sys.executable,
                    "-u",
                    "-c",
                    (
                        "import sys,time; "
                        "print('ORDAX_STDIN_READY', flush=True); "
                        "value=sys.stdin.readline().rstrip('\\r\\n'); "
                        "print('ORDAX_STDIN_GOT:'+value, flush=True); "
                        "time.sleep(5)"
                    ),
                ],
                "wait_seconds": 1.5,
            },
        )
        self.assertTrue(started.ok, started.summary)
        self.process_id = started.data["process_id"]

        written = self.registry.execute(
            "process.write_stdin",
            {
                "project": "demo",
                "process_id": self.process_id,
                "text": "hello-ordax",
                "newline": True,
            },
        )
        self.assertTrue(written.ok, written.summary)

        tail = ""
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            logs = self.registry.execute(
                "process.logs",
                {
                    "project": "demo",
                    "process_id": self.process_id,
                    "max_bytes": 32768,
                },
            )
            self.assertTrue(logs.ok, logs.summary)
            tail = logs.data["tail"]
            if "ORDAX_STDIN_GOT:hello-ordax" in tail:
                break
            time.sleep(0.1)
        self.assertIn("ORDAX_STDIN_GOT:hello-ordax", tail)

    def test_live_managed_handle_is_authoritative_before_windows_pid_probe(self):
        process_id = "11111111-1111-4111-8111-111111111111"
        handle = SimpleNamespace(pid=4242, poll=lambda: None)
        self.registry._persistent_process_handles = {process_id: handle}
        state = {
            "process_id": process_id,
            "project": "demo",
            "manager_pid": 4242,
            "token": "owned-token",
            "state": "starting",
        }

        with patch.object(self.registry, "_pid_running", return_value=False):
            public = self.registry._public_process_state(state)

        self.assertTrue(public["running"])
        self.assertTrue(public["ownership_valid"])
        self.assertEqual("running", public["state"])

    def test_process_id_is_project_scoped(self):
        result = self.registry.execute(
            "process.status",
            {
                "project": "demo",
                "process_id": "not-a-uuid",
            },
        )
        self.assertFalse(result.ok)
        self.assertIn("UUID", result.summary)


if __name__ == "__main__":
    unittest.main()
