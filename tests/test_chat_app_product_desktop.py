from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from ordax_chat_app.product_desktop import ProductDesktopApi
from ordax_studio.product_auth import ProductAccountError


class FakeAutonomy:
    def status(self):
        return {"running": False}

    def resume_persisted(self):
        return self.status()

    def stop(self, **_kwargs):
        return self.status()


class FakeWebBridge:
    def status(self):
        return {
            "configured": False,
            "enabled": False,
            "running": False,
            "client_installed": False,
            "daemon": {"state": "not-running", "heartbeat_fresh": False},
        }


class ProductDesktopTests(unittest.TestCase):
    def setUp(self):
        config = types.SimpleNamespace(
            device_id="device-123",
            control_plane_url="https://control.example",
        )
        runtime = types.SimpleNamespace(
            agent=types.SimpleNamespace(config=config),
        )
        self.api = ProductDesktopApi(
            runtime,
            autonomy=FakeAutonomy(),
            web_bridge=FakeWebBridge(),
            auto_resume=False,
        )

    def test_device_status_preserves_product_identity_surface(self):
        status = self.api.ordax_device_status()
        self.assertTrue(status["ok"])
        self.assertTrue(status["data"]["enrolled"])
        self.assertTrue(status["data"]["control_plane_configured"])
        self.assertEqual(status["data"]["device_id"], "device-123")

    @patch("ordax_chat_app.product_desktop.connect_existing_device")
    def test_connect_ordax_account_uses_existing_secure_pairing(self, connect):
        connect.return_value = {
            "email": "user@example.com",
            "link": {"device_id": "device-123"},
        }
        result = self.api.connect_ordax_account("user@example.com", "secret")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["email"], "user@example.com")
        connect.assert_called_once()
        args = connect.call_args.args
        self.assertEqual(args[0].device_id, "device-123")
        self.assertEqual(args[1], "user@example.com")
        self.assertEqual(args[2], "secret")

    @patch("ordax_chat_app.product_desktop.connect_existing_device")
    def test_connect_ordax_account_preserves_safe_product_errors(self, connect):
        connect.side_effect = ProductAccountError(
            "product_auth_rejected",
            "E-mail ou senha não conferem.",
        )
        result = self.api.connect_ordax_account("user@example.com", "wrong")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "product_auth_rejected")
        self.assertEqual(result["summary"], "E-mail ou senha não conferem.")


if __name__ == "__main__":
    unittest.main()
