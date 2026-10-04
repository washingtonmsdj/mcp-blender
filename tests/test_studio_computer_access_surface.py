from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class StudioComputerAccessSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.product_html = (ROOT / "ordax_studio" / "studio_product.html").read_text(encoding="utf-8")
        self.legacy_html = (ROOT / "ordax_studio" / "studio.html").read_text(encoding="utf-8")
        self.studio_js = (ROOT / "ordax_studio" / "assets" / "studio.js").read_text(encoding="utf-8")
        self.access_js = (ROOT / "ordax_studio" / "assets" / "computer_access.js").read_text(encoding="utf-8")
        self.bridge = (ROOT / "ordax_studio" / "workbench_bridge.py").read_text(encoding="utf-8")
        self.product_mcp = (ROOT / "ordax_dev_agent" / "product_mcp.py").read_text(encoding="utf-8")

    def test_canonical_surface_has_first_class_computer_access_view(self) -> None:
        self.assertIn('data-view="computer"', self.product_html)
        self.assertIn('id="computerCanvas"', self.product_html)
        self.assertIn('assets/computer_access.css', self.product_html)
        self.assertIn('assets/computer_access.js', self.product_html)
        self.assertIn("computer:'Acesso ao computador'", self.studio_js)
        self.assertIn("view==='computer'", self.studio_js)
        self.assertIn("await loadComputerAccess()", self.studio_js)

    def test_legacy_html_is_redirect_only_not_second_surface(self) -> None:
        self.assertIn("studio_product.html", self.legacy_html)
        self.assertNotIn('id="computerCanvas"', self.legacy_html)
        self.assertNotIn('id="projectGrid"', self.legacy_html)
        self.assertNotIn('assets/studio.js', self.legacy_html)

    def test_policy_editor_is_local_owner_control_with_revision_guard(self) -> None:
        self.assertIn("computer_access_settings", self.access_js)
        self.assertIn("save_computer_access_settings", self.access_js)
        self.assertIn("expected_revision", self.access_js)
        self.assertIn("window.confirm", self.access_js)
        self.assertIn("grants MCP continuam obrigatórios", self.access_js)
        self.assertIn('"computer_access_settings"', self.bridge)
        self.assertIn('"save_computer_access_settings"', self.bridge)

    def test_remote_product_mcp_cannot_mutate_local_policy(self) -> None:
        self.assertNotIn("computer.access_update", self.product_mcp)
        self.assertNotIn("save_computer_access_settings", self.product_mcp)


if __name__ == "__main__":
    unittest.main()
