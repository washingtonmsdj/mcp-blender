from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ordax_studio.openai_tunnel import (
    PROFILE_NAME,
    TASK_NAME,
    TUNNEL_CLIENT_ARCHIVE,
    TUNNEL_CLIENT_SHA256,
    TUNNEL_CLIENT_URL,
    TUNNEL_CLIENT_VERSION,
    OpenAITunnelError,
    OpenAITunnelManager,
    _safe_extract,
)
from ordax_studio.openai_tunnel_ui import HTML


class OpenAITunnelTests(unittest.TestCase):
    def test_official_release_is_version_pinned_and_hash_pinned(self):
        self.assertEqual(TUNNEL_CLIENT_VERSION, "v0.0.15")
        self.assertEqual(len(TUNNEL_CLIENT_SHA256), 64)
        int(TUNNEL_CLIENT_SHA256, 16)
        self.assertIn(TUNNEL_CLIENT_VERSION, TUNNEL_CLIENT_URL)
        self.assertTrue(TUNNEL_CLIENT_URL.endswith(TUNNEL_CLIENT_ARCHIVE))
        self.assertEqual(PROFILE_NAME, "ordax-studio")
        self.assertEqual(TASK_NAME, "ORDAX OpenAI MCP Tunnel")

    def test_safe_extract_rejects_zip_slip(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../outside.txt", "no")
            with self.assertRaises(OpenAITunnelError):
                _safe_extract(archive, root / "out")

    def test_status_never_exposes_runtime_api_key(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = root / "state"
            state.mkdir()
            managed = root / "managed"
            manager = OpenAITunnelManager(state_dir=state, managed_repo=managed)
            manager.config_path.write_text(
                json.dumps({
                    "tunnel_id": "tunnel_0123456789abcdef0123456789abcdef",
                    "profile": PROFILE_NAME,
                    "doctor_ok": True,
                }),
                encoding="utf-8",
            )
            manager.secret_path.write_text("encrypted-secret-placeholder", encoding="ascii")
            status = manager.status()
            self.assertTrue(status["configured"])
            serialized = json.dumps(status).lower()
            self.assertNotIn("api_key", serialized)
            self.assertNotIn("secret-placeholder", serialized)

    def test_ui_uses_password_input_and_clears_secret_after_call(self):
        self.assertIn('type="password"', HTML)
        self.assertIn("pywebview.api.connect", HTML)
        self.assertGreaterEqual(HTML.count("el('key').value=''"), 2)
        self.assertNotIn("localStorage", HTML)
        self.assertNotIn("sessionStorage", HTML)

    def test_windows_installer_exposes_chatgpt_connector_shortcut(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "windows" / "ordax-studio-install.ps1").read_text(encoding="utf-8")
        self.assertIn("Conectar ChatGPT.lnk", script)
        self.assertIn("ordax_studio.openai_tunnel_ui", script)
        self.assertIn("chatgpt_connector", script)
        self.assertNotIn("blendmcp_legacy", script)


if __name__ == "__main__":
    unittest.main()
