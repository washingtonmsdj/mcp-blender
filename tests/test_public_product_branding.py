from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicProductBrandingTests(unittest.TestCase):
    def test_public_surfaces_use_ordax_studio_name(self) -> None:
        public_pages = (ROOT / "control-plane" / "cloudflare" / "src" / "public_pages.ts").read_text(encoding="utf-8")
        consent = (ROOT / "control-plane" / "cloudflare" / "src" / "oauth_consent.ts").read_text(encoding="utf-8")
        mcp = (ROOT / "control-plane" / "cloudflare" / "src" / "mcp_http.ts").read_text(encoding="utf-8")

        self.assertIn('const PRODUCT_NAME = "ORDAX Studio"', public_pages)
        self.assertIn("Autorizar ORDAX Studio", consent)
        self.assertIn('serverInfo: { name: "ORDAX Studio", version: "0.4.1" }', mcp)
        self.assertNotIn("ORDAX Dev", public_pages)
        self.assertNotIn("ORDAX Dev", consent)

    def test_historical_windows_binary_name_remains_explicit_compatibility(self) -> None:
        document = (ROOT / "docs" / "ORDAX_STUDIO_WINDOWS_PRODUCT.md").read_text(encoding="utf-8")
        self.assertIn("ORDAX Studio para Windows", document)
        self.assertIn("ORDAX Dev.exe", document)
        self.assertIn("legado/compatível", document)
        self.assertIn("compatibilidade", document)


if __name__ == "__main__":
    unittest.main()
