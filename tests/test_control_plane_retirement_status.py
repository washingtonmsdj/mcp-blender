from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult


class ControlPlaneRetirementStatusTests(unittest.TestCase):
    def make_config(self, root: Path) -> AgentConfig:
        return AgentConfig(
            agent_name="retirement-test",
            supabase_url=None,
            poll_seconds=5.0,
            state_dir=root / "state",
            agent_repo_path=root / "agent",
            hordax_path=root / "hordax",
            bridge_path=root / "bridge",
        )

    def test_action_is_registered_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry = ActionRegistry(self.make_config(root))
            self.assertIn(
                "agent.control_plane_retirement_status",
                registry.names,
            )

        repo_root = Path(__file__).resolve().parents[1]
        script = (
            repo_root
            / "scripts"
            / "windows"
            / "ordax-cloudflare-v3-retirement-status.ps1"
        ).read_text(encoding="utf-8")

        for forbidden in (
            "Remove-Item",
            "Move-Item",
            "Set-Content",
            "WriteAllText",
            "SetEnvironmentVariable",
            "Add-Member",
        ):
            self.assertNotIn(forbidden, script)

        self.assertIn("ready_for_repository_v2_removal", script)
        self.assertIn("FINALIZED_PROOF_MISSING", script)
        self.assertIn("DEVELOPMENT_V2_LOCAL_STATE_NOT_RETIRED", script)
        self.assertIn("CLOUDFLARE_V3_CREDENTIAL_MISSING", script)
        self.assertIn("DEVELOPMENT_V2_CREDENTIALS_STILL_PRESENT", script)
        self.assertIn("LIVE_PROTOCOL_NOT_CLOUDFLARE_V3", script)
        self.assertIn("LIVE_HEARTBEAT_STALE", script)

    def test_action_executes_only_owned_script_and_parses_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "agent"
            script = (
                repo
                / "scripts"
                / "windows"
                / "ordax-cloudflare-v3-retirement-status.ps1"
            )
            script.parent.mkdir(parents=True)
            script.write_text("# test\n", encoding="utf-8")
            registry = ActionRegistry(self.make_config(root))
            expected = {
                "ready_for_repository_v2_removal": True,
                "blockers": [],
            }
            fake = ActionResult(
                True,
                "ok",
                {"stdout": json.dumps(expected)},
            )

            with patch(
                "ordax_dev_agent.agent_actions.sys.platform",
                "win32",
            ), patch(
                "ordax_dev_agent.agent_actions._run",
                return_value=fake,
            ) as run:
                result = registry.execute(
                    "agent.control_plane_retirement_status",
                    {"timeout_seconds": 10},
                )

            self.assertTrue(result.ok)
            self.assertEqual(expected, result.data["retirement"])
            command = run.call_args.args[0]
            self.assertEqual("powershell.exe", command[0])
            self.assertEqual(str(script), command[-1])
            self.assertNotIn("-Command", command)

    def test_action_rejects_unknown_fields_and_non_windows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = ActionRegistry(self.make_config(Path(raw)))
            unknown = registry.execute(
                "agent.control_plane_retirement_status",
                {"script": "anything.ps1"},
            )
            self.assertFalse(unknown.ok)
            self.assertIn("unsupported field", unknown.summary)

            with patch(
                "ordax_dev_agent.agent_actions.sys.platform",
                "linux",
            ):
                result = registry.execute(
                    "agent.control_plane_retirement_status",
                    {},
                )
            self.assertFalse(result.ok)
            self.assertIn("only on Windows", result.summary)


if __name__ == "__main__":
    unittest.main()
