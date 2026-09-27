from __future__ import annotations

import unittest
from pathlib import Path


class LegacyV1RemovalTests(unittest.TestCase):
    def test_legacy_v1_runtime_and_sdk_are_gone(self) -> None:
        root = Path(__file__).resolve().parents[1]
        control = (root / "ordax_dev_agent" / "control_plane.py").read_text(
            encoding="utf-8"
        )
        config = (root / "ordax_dev_agent" / "config.py").read_text(
            encoding="utf-8"
        )
        main = (root / "ordax_dev_agent" / "main.py").read_text(encoding="utf-8")
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        installer = (
            root / "scripts" / "windows" / "ordax-agent-install.ps1"
        ).read_text(encoding="utf-8")

        for text in (control, config, main):
            self.assertNotIn("legacy-v1", text)

        self.assertNotIn("from supabase import", control)
        self.assertNotIn('"supabase>=', pyproject)
        self.assertNotIn("publishable_key", config)
        self.assertNotIn("PublishableKey", installer)
        self.assertNotIn("PairingCode", installer)
        self.assertNotIn("pairing-code.txt", installer)
        self.assertNotIn("import httpx, mcp, supabase", installer)

        self.assertIn('protocol == "development-v2"', control)
        self.assertIn('protocol == "cloudflare-v3"', control)
        self.assertIn('control_plane_protocol: str = "development-v2"', config)

    def test_only_v2_migration_supabase_pieces_remain(self) -> None:
        root = Path(__file__).resolve().parents[1]

        self.assertFalse(
            (root / "control-plane" / "supabase" / "001_dev_agent_control_plane.sql").exists()
        )
        self.assertFalse(
            (
                root
                / "control-plane"
                / "supabase"
                / "functions"
                / "ordax-dev-agent"
                / "index.ts"
            ).exists()
        )

        self.assertTrue(
            (
                root
                / "control-plane"
                / "supabase"
                / "functions"
                / "ordax-device-setup"
                / "index.ts"
            ).is_file()
        )
        self.assertTrue(
            (root / "ordax_dev_agent" / "development_control_plane.py").is_file()
        )
        self.assertTrue(
            (root / "ordax_dev_agent" / "cloudflare_control_plane.py").is_file()
        )


if __name__ == "__main__":
    unittest.main()
