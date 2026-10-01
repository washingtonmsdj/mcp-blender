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

    def test_status_recovers_owned_runtime_after_desktop_restart(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        manager.configure("tunnel_0123456789abcdef", "secret")
        binary = manager.bin_dir / ("tunnel-client.exe" if __import__("os").name == "nt" else "tunnel-client")
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_bytes(b"binary")
        manager._write_runtime({
            "schema_version": 1,
            "pid": 4242,
            "profile": "ordax-dev",
            "binary": str(binary),
            "started_at_unix": 123.0,
        })
        with patch.object(manager, "_pid_running", return_value=True), patch.object(
            manager, "_commandline", return_value=f'"{binary}" run --profile ordax-dev'
        ):
            status = manager.status()
        self.assertTrue(status["running"])
        self.assertEqual(status["pid"], 4242)
        self.assertEqual(status["started_at_unix"], 123.0)

    def test_stale_or_reused_pid_is_not_adopted(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        manager.configure("tunnel_0123456789abcdef", "secret")
        binary = manager.bin_dir / ("tunnel-client.exe" if __import__("os").name == "nt" else "tunnel-client")
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_bytes(b"binary")
        manager._write_runtime({
            "schema_version": 1,
            "pid": 4242,
            "profile": "ordax-dev",
            "binary": str(binary),
            "started_at_unix": 123.0,
        })
        with patch.object(manager, "_pid_running", return_value=True), patch.object(
            manager, "_commandline", return_value="python unrelated.py"
        ):
            status = manager.status()
        self.assertFalse(status["running"])
        self.assertIsNone(status["pid"])
        self.assertFalse(manager.runtime_path.exists())

    def test_desired_state_is_separate_from_credentials(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        status = manager.configure("tunnel_0123456789abcdef", "secret")
        self.assertTrue(status["configured"])
        self.assertFalse(status["enabled"])

        enabled = manager.set_enabled(True)
        self.assertTrue(enabled["enabled"])
        disabled = manager.set_enabled(False)
        self.assertFalse(disabled["enabled"])
        self.assertTrue(disabled["configured"])

    def test_non_windows_startup_status_is_explicitly_unsupported(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        with patch("ordax_chat_app.web_bridge.os.name", "posix"):
            status = manager.startup_status()
        self.assertFalse(status["supported"])
        self.assertFalse(status["installed"])

    def test_headless_environment_injects_packaged_runtime_paths(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        with patch.object(manager, "_product_root", return_value=self.root / "product"), patch.dict(
            "ordax_chat_app.web_bridge.os.environ",
            {"PATH": "test"},
            clear=True,
        ):
            env = manager._env({"api_key": "runtime-secret"})
        self.assertEqual(env["CONTROL_PLANE_API_KEY"], "runtime-secret")
        self.assertEqual(env["ORDAX_PACKAGED_ROOT"], str(self.root / "product"))
        self.assertEqual(env["ORDAX_AGENT_REPO_PATH"], str(self.root / "product"))
        self.assertEqual(env["ORDAX_BRIDGE_PATH"], str(self.root / "product"))

    def test_disconnect_clears_credentials(self):
        manager = WebBridgeManager(state_dir=self.root, credentials=self.store)
        manager.configure("tunnel_0123456789abcdef", "secret")
        manager.disconnect()
        self.assertFalse(manager.status()["configured"])


if __name__ == "__main__":
    unittest.main()
