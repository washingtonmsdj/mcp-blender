from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StudioSingleSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.product = (ROOT / "ordax_studio" / "studio_product.html").read_text(encoding="utf-8")
        self.legacy = (ROOT / "ordax_studio" / "studio.html").read_text(encoding="utf-8")
        self.project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def test_product_surface_is_the_only_full_studio_ui(self) -> None:
        for marker in (
            'id="projectHome"',
            'id="projectGrid"',
            'id="workspace"',
            'id="sessionsCanvas"',
            'id="computerCanvas"',
            'src="assets/studio.js"',
        ):
            self.assertIn(marker, self.product)
            self.assertNotIn(marker, self.legacy)

    def test_legacy_html_is_bounded_compatibility_redirect(self) -> None:
        self.assertIn('url=studio_product.html', self.legacy)
        self.assertIn("location.replace('studio_product.html')", self.legacy)
        self.assertLess(len(self.legacy.encode("utf-8")), 1024)
        self.assertNotIn('assets/studio.css', self.legacy)
        self.assertNotIn('host_bridge.js', self.legacy)

    def test_all_packaged_web_entrypoints_use_canonical_product_host(self) -> None:
        scripts = self.project["project"]["scripts"]
        self.assertEqual("ordax_studio.product_web_desktop:main", scripts["ordax-studio-web"])
        self.assertEqual("ordax_studio.product_web_desktop:main", scripts["ordax-dev"])


if __name__ == "__main__":
    unittest.main()
