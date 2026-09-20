import unittest
from pathlib import Path


class AgentSelfHealScriptTests(unittest.TestCase):
    def test_launcher_and_recovery_use_shared_update_policy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        launcher = (root / "scripts" / "windows" / "ordax-agent-start.cmd").read_text(
            encoding="utf-8"
        )
        recovery = (
            root / ".github" / "workflows" / "ordax-agent-recovery.yml"
        ).read_text(encoding="utf-8")

        for text in (launcher, recovery):
            self.assertIn(
                "ordax_dev_agent.update_policy --check-clean",
                text,
            )
            self.assertNotIn("diff-files --quiet", text)
            self.assertNotIn("diff-index --cached", text)

    def test_launcher_control_flow_is_structurally_intact(self) -> None:
        root = Path(__file__).resolve().parents[1]
        launcher = (
            root / "scripts" / "windows" / "ordax-agent-start.cmd"
        ).read_text(encoding="utf-8")

        self.assertEqual(1, launcher.splitlines().count(":run"))
        self.assertEqual(1, launcher.splitlines().count(":safe_update"))
        self.assertEqual(1, launcher.splitlines().count(":increase_backoff"))

        expected_run_block = (
            ':run\n'
            'if "%SKIP_SAFE_UPDATE%"=="0" (\n'
            '  call :safe_update\n'
            ') else (\n'
            '  set "SKIP_SAFE_UPDATE=0"\n'
            ')\n'
        )
        self.assertIn(expected_run_block, launcher)

        run_index = launcher.index(":run")
        compile_index = launcher.index(
            '"%PYTHON%" -m compileall',
            run_index,
        )
        safe_label_index = launcher.index("\n:safe_update\n")
        self.assertLess(run_index, compile_index)
        self.assertLess(compile_index, safe_label_index)

        self.assertIn(
            'ordax_dev_agent.update_policy --check-clean "%ROOT%"',
            launcher,
        )
        self.assertNotIn("diff-files --quiet", launcher)
        self.assertNotIn("diff-index --cached", launcher)

    def test_watchdog_requests_restart_only_after_successor_check(self) -> None:
        root = Path(__file__).resolve().parents[1]
        watchdog = (
            root / "scripts" / "windows" / "ordax-agent-watchdog.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("function Request-AgentRestartIfNeeded", watchdog)
        self.assertIn("*ordax_dev_agent.main*", watchdog)
        self.assertIn(
            "Start-ScheduledTask -TaskName $RestartTaskName",
            watchdog,
        )
        self.assertIn('$task.State -eq "Running"', watchdog)
        self.assertIn('$task.State -eq "Disabled"', watchdog)

        exit_index = watchdog.index("EXIT parent process ended")
        restart_index = watchdog.index(
            "Request-AgentRestartIfNeeded",
            exit_index,
        )
        self.assertGreater(restart_index, exit_index)



if __name__ == "__main__":
    unittest.main()
