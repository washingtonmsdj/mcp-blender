from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "ordax-studio"


class OrdaxStudioPluginPackageTests(unittest.TestCase):
    def test_portable_plugin_manifest_is_valid(self):
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(manifest["name"], "ordax-studio")
        self.assertEqual(manifest["extensions"]["com.openai"]["interface"]["displayName"], "ORDAX Studio")

    def test_plugin_uses_production_streamable_http_mcp(self):
        config = json.loads((PLUGIN_ROOT / "mcp.json").read_text(encoding="utf-8-sig"))
        server = config["mcpServers"]["ordax"]
        self.assertEqual(server["type"], "streamable-http")
        self.assertEqual(server["url"], "https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp")


if __name__ == "__main__":
    unittest.main()
