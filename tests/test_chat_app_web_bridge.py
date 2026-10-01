from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_chat_app.web_bridge import (
    WebBridgeCredentialStore,
    WebBridgeManager,
    _platform_asset_fragment,
)


class WebBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = WebBridgeCredentialStore(
            self.root / "bridge.dat",
            protect=lambda value: value,
            unprotect=lambda value: value,
        )

    def test_credentials_round_trip_without_exposing_key_in_status(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        status = manager.configure("tunnel_0123456789abcdef", "sk-runtime-secret")
        self.assertTrue(status["configured"])
        self.assertEqual(status["tunnel_id"], "tunnel_0123456789abcdef")
        self.assertNotIn("api_key", status)
        payload = self.store.load()
        self.assertEqual(payload["api_key"], "sk-runtime-secret")

    def test_reconfigure_same_tunnel_preserves_initialized_state(self):
        self.store.save({
            "version": 1,
            "tunnel_id": "tunnel_0123456789abcdef",
            "api_key": "old",
            "profile": "ordax-dev",
            "initialized": True,
        })
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        manager.configure("tunnel_0123456789abcdef", "new")
        self.assertTrue(self.store.load()["initialized"])
        manager.configure("tunnel_fedcba9876543210", "newer")
        self.assertFalse(self.store.load()["initialized"])

    def test_invalid_tunnel_id_is_rejected(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        with self.assertRaisesRegex(ValueError, "Tunnel ID"):
            manager.configure("not-a-tunnel", "secret")

    def test_platform_asset_mapping(self):
        with patch("ordax_chat_app.web_bridge.platform.system", return_value="Windows"), patch(
            "ordax_chat_app.web_bridge.platform.machine", return_value="AMD64"
        ):
            self.assertEqual(_platform_asset_fragment(), "-windows-amd64.zip")
        with patch("ordax_chat_app.web_bridge.platform.system", return_value="Linux"), patch(
            "ordax_chat_app.web_bridge.platform.machine", return_value="aarch64"
        ):
            self.assertEqual(_platform_asset_fragment(), "-linux-arm64.zip")

    def test_disconnect_clears_credentials(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        manager.configure("tunnel_0123456789abcdef", "secret")
        manager.disconnect()
        self.assertFalse(manager.status()["configured"])


if __name__ == "__main__":
    unittest.main()
