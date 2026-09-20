import unittest
from pathlib import Path


class AgentSelfHealScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]

    def test_launcher_uses_bounded_worktree_verifier(self) -> None:
        launcher = (
            self.root / "scripts" / "windows" / "ordax-agent-start.cmd"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "ordax_dev_agent.update_policy --check-worktree",
            launcher,
        )
        self.assertNotIn("diff-files --quiet", launcher)
        self.assertIn("diff-index --cached --quiet HEAD", launcher)

    def test_watchdog_requests_restart_only_after_successor_check(self) -> None:
        watchdog = (
            self.root / "scripts" / "windows" / "ordax-agent-watchdog.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("function Request-AgentRestartIfNeeded", watchdog)
        self.assertIn("*ordax_dev_agent.main*", watchdog)
        self.assertIn("Start-ScheduledTask -TaskName $RestartTaskName", watchdog)
        self.assertIn('$task.State -eq "Running"', watchdog)
        self.assertIn('$task.State -eq "Disabled"', watchdog)
        exit_index = watchdog.index("EXIT parent process ended")
        restart_index = watchdog.index("Request-AgentRestartIfNeeded", exit_index)
        self.assertGreater(restart_index, exit_index)


if __name__ == "__main__":
    unittest.main()
