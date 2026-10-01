from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

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
