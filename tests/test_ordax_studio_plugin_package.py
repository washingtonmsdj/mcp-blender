from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_ordax_plugin import build_archive

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "ordax-studio"


class OrdaxStudioPluginPackageTests(unittest.TestCase):
    def test_portable_plugin_manifest_is_valid(self):
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(manifest["name"], "ordax-dev")
        self.assertEqual(manifest["extensions"]["com.openai"]["interface"]["displayName"], "ORDAX Dev")

    def test_plugin_uses_production_streamable_http_mcp(self):
        config = json.loads((PLUGIN_ROOT / "mcp.json").read_text(encoding="utf-8-sig"))
        server = config["mcpServers"]["ordax"]
        self.assertEqual(server["type"], "streamable-http")
        self.assertEqual(server["url"], "https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp")


    def test_manifests_are_utf8_without_bom(self):
        for name in ("plugin.json", "mcp.json"):
            self.assertFalse((PLUGIN_ROOT / name).read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_builder_produces_deterministic_portable_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            first, first_sha = build_archive(Path(directory) / "a")
            second, second_sha = build_archive(Path(directory) / "b")
            self.assertEqual(first_sha, second_sha)
            with zipfile.ZipFile(first) as bundle:
                self.assertEqual(
                    sorted(bundle.namelist()),
                    ["assets/ordax.svg", "mcp.json", "plugin.json"],
                )

    def test_public_submission_metadata_is_complete(self):
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
        interface = manifest["extensions"]["com.openai"]["interface"]
        self.assertLessEqual(len(interface["displayName"]), 30)
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        for field in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
            self.assertTrue(interface[field].startswith("https://"))
        self.assertEqual(interface["composerIcon"], "./assets/ordax.svg")
        self.assertEqual(interface["logo"], "./assets/ordax.svg")
        review = manifest["extensions"]["com.openai"]["review"]["test_cases"]
        self.assertEqual(len(review["positive"]), 5)
        self.assertEqual(len(review["negative"]), 3)

    def test_submission_assets_are_present(self):
        self.assertTrue((PLUGIN_ROOT / "assets" / "ordax.svg").is_file())



if __name__ == "__main__":
    unittest.main()
