import unittest
from pathlib import Path

from ordax_dev_agent.config import AgentConfig


class CloudflareCutoverTests(unittest.TestCase):
    def test_cutover_is_transactional_and_has_emergency_rollback(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = (
            root / "scripts" / "windows" / "ordax-cloudflare-v3-cutover.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("Local\\OrdaXDeviceSetup", script)
        self.assertIn("AGENT_BUSY_CUTOVER_REFUSED", script)
        self.assertIn("agent-settings.pre-cloudflare-v3.json", script)
        self.assertIn("cloudflare-v3-cutover.json", script)
        self.assertIn("ordax_dev_agent.device_credentials", script)
        self.assertIn("Restore-V2ActiveSettings", script)
        self.assertIn("RequireRemoteHeartbeat", script)
        self.assertIn("awaiting-reboot-proof", script)
        self.assertIn("Emergency v2 rollback completed", script)
        self.assertIn("CLOUDFLARE_V3_CUTOVER_AND_V2_ROLLBACK_FAILED", script)
        self.assertNotIn("Get-CimInstance", script)

        enrollment_index = script.index(
            "'--protocol', 'cloudflare-v3'"
        )
        restart_index = script.index(
            "Restart-ManagedAgent -OldPid $oldPid"
        )
        self.assertLess(enrollment_index, restart_index)

        restore_index = script.index(
            "$rollbackIdentity = Restore-V2ActiveSettings"
        )
        rollback_restart_index = script.index(
            "Restart-ManagedAgent -OldPid $rollbackOldPid"
        )
        self.assertLess(restore_index, rollback_restart_index)

    def test_public_status_exposes_non_secret_control_plane_url(self) -> None:
        root = Path("/tmp/ordax-cutover-test")
        config = AgentConfig(
            agent_name="test",
            supabase_url=None,
            publishable_key=None,
            poll_seconds=1.0,
            state_dir=root,
            agent_repo_path=root,
            hordax_path=root,
            bridge_path=root,
            control_plane_protocol="cloudflare-v3",
            development_device_id="22222222-2222-4222-8222-222222222222",
            control_plane_url="https://ordax.example.workers.dev",
        )

        status = config.public_status()

        self.assertEqual("cloudflare-v3", status["control_plane_protocol"])
        self.assertEqual(
            "https://ordax.example.workers.dev",
            status["control_plane_url"],
        )


if __name__ == "__main__":
    unittest.main()
