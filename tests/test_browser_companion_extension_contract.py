from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "browser_extension"


class BrowserCompanionExtensionContractTests(unittest.TestCase):
    def test_manifest_is_scoped_to_chatgpt_and_loopback(self):
        manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        hosts = set(manifest["host_permissions"])
        self.assertIn("https://chatgpt.com/*", hosts)
        self.assertIn("http://127.0.0.1:8775/*", hosts)
        self.assertFalse(any(host == "<all_urls>" for host in hosts))
        self.assertEqual(set(manifest["permissions"]), {"storage"})

    def test_loopback_bootstrap_script_is_declared(self):
        manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
        scripts = manifest.get("content_scripts", [])
        bootstrap = [
            item for item in scripts
            if "bootstrap.js" in item.get("js", [])
        ]
        self.assertEqual(len(bootstrap), 1)
        self.assertIn(
            "http://127.0.0.1:8775/bootstrap*",
            bootstrap[0].get("matches", []),
        )

    def test_background_owns_pairing_token(self):
        background = (EXT / "background.js").read_text(encoding="utf-8")
        content = (EXT / "content.js").read_text(encoding="utf-8")
        self.assertIn('chrome.storage.local.set({token, browserId})', background)
        self.assertNotIn("Bearer ", content)
        self.assertNotIn("token =", content)

    def test_background_auto_pairs_on_extension_startup(self):
        background = (EXT / "background.js").read_text(encoding="utf-8")
        self.assertIn('async function autoPair()', background)
        self.assertIn('api("/pairing")', background)
        self.assertIn('chrome.runtime.onInstalled.addListener', background)
        self.assertIn('chrome.runtime.onStartup.addListener', background)

    def test_content_script_uses_page_ui_not_private_chatgpt_api(self):
        content = (EXT / "content.js").read_text(encoding="utf-8")
        self.assertIn("#prompt-textarea", content)
        self.assertIn("data-testid='send-button'", content)
        self.assertNotIn("/backend-api/", content)
        self.assertNotIn("Authorization", content)

    def test_loopback_bootstrap_is_versioned_and_scoped(self):
        manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
        bootstrap = next(
            item for item in manifest["content_scripts"]
            if "bootstrap.js" in item.get("js", [])
        )
        self.assertEqual(
            bootstrap["matches"],
            ["http://127.0.0.1:8775/bootstrap*"],
        )
        source = (EXT / "bootstrap.js").read_text(encoding="utf-8")
        self.assertIn('type: "ordax.pair"', source)
        self.assertIn('location.replace("https://chatgpt.com/")', source)
        self.assertNotIn("/backend-api/", source)

    def test_windows_product_includes_extension(self):
        script = (ROOT / "scripts" / "windows" / "build-ordax-studio-product.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('Join-Path $repoRoot "browser_extension"', script)
        self.assertIn('Join-Path $stageRoot "browser_extension"', script)


if __name__ == "__main__":
    unittest.main()
