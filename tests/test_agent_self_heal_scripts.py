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


if __name__ == "__main__":
    unittest.main()
