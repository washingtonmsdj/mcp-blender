from pathlib import Path
import unittest


class OrdaxStudioBlenderConnectionAssetTests(unittest.TestCase):
    def test_html_loads_blender_connection_component(self):
        root = Path(__file__).resolve().parents[1] / "ordax_studio"
        html = (root / "studio.html").read_text(encoding="utf-8")
        self.assertIn('href="assets/blender-connection.css"', html)
        self.assertIn('src="assets/blender-connection.js"', html)
        self.assertLess(
            html.index('src="assets/studio.js"'),
            html.index('src="assets/blender-connection.js"'),
        )

    def test_connection_controller_exposes_all_actionable_states(self):
        root = Path(__file__).resolve().parents[1] / "ordax_studio" / "assets"
        script = (root / "blender-connection.js").read_text(encoding="utf-8")
        for state in ("connected", "adopted", "restart_required", "ambiguous"):
            self.assertIn(state, script)
        for api in (
            "blender_prepare",
            "blender_install_bridge",
            "blender_adopt",
            "blender_start",
        ):
            self.assertIn(api, script)
        self.assertIn("Adotar PID", script)
        self.assertIn("Instalar bridge", script)
        self.assertIn("Abrir Blender", script)

    def test_connection_component_has_responsive_styles(self):
        root = Path(__file__).resolve().parents[1] / "ordax_studio" / "assets"
        stylesheet = (root / "blender-connection.css").read_text(encoding="utf-8")
        self.assertIn(".blenderConnectionCard", stylesheet)
        self.assertIn(".blenderConnectionActions", stylesheet)
        self.assertIn("@media", stylesheet)


if __name__ == "__main__":
    unittest.main()
