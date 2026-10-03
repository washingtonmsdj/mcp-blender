from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkbenchComputerFirstUiTests(unittest.TestCase):
    def test_native_workbench_is_a_thin_host_for_the_studio_surface(self) -> None:
        xaml = (ROOT / "native" / "ordax-workbench" / "MainWindow.xaml").read_text(encoding="utf-8")
        self.assertIn('Title="ORDAX Studio"', xaml)
        self.assertIn('Header="Projeto"', xaml)
        self.assertIn('x:Name="StudioView"', xaml)
        self.assertIn('Header="Web IA"', xaml)
        self.assertIn('Header="Preview"', xaml)
        self.assertIn('Header="Browser"', xaml)
        self.assertIn('Header="Execuções"', xaml)
        self.assertIn('Header="Diagnóstico"', xaml)
        self.assertIn('x:Name="ProviderView"', xaml)
        self.assertIn('x:Name="ComputerControlState"', xaml)
        self.assertIn('x:Name="DeviceCardState"', xaml)
        self.assertIn('x:Name="McpCardState"', xaml)
        self.assertIn('x:Name="TopConnectionDot"', xaml)
        self.assertNotIn('Header="Visão geral"', xaml)
        self.assertNotIn('Text="COMPUTADOR"', xaml)
        self.assertNotIn('Text="CAPACIDADES ESPECIALIZADAS"', xaml)

    def test_shared_surface_owns_project_navigation_and_preview(self) -> None:
        html = (ROOT / "ordax_studio" / "studio_product.html").read_text(encoding="utf-8")
        css = (ROOT / "ordax_studio" / "assets" / "studio.css").read_text(encoding="utf-8")
        self.assertIn("<title>ORDAX Studio</title>", html)
        self.assertIn('class="projectSidebar"', html)
        self.assertIn('class="mainPane"', html)
        self.assertIn('class="previewPane"', html)
        self.assertIn('class="statusbar"', html)
        self.assertIn('--sidebar:286px', css)
        self.assertIn('--preview:minmax(460px,42%)', css)
        self.assertIn('grid-template-columns:var(--sidebar) minmax(460px,1fr) var(--preview)', css)
        # Global operating-system navigation belongs to prototipo-ordax-os, not Studio.
        self.assertNotIn('>Network<', html)
        self.assertNotIn('>Ajustes<', html)
        self.assertNotIn('>Sistema<', html)

    def test_status_surface_uses_real_computer_control_contract(self) -> None:
        api = (ROOT / "ordax_studio" / "web_desktop.py").read_text(encoding="utf-8")
        code = (ROOT / "native" / "ordax-workbench" / "MainWindow.xaml.cs").read_text(encoding="utf-8")
        self.assertIn('"computer_control": computer_control', api)
        self.assertIn('"computer.screenshot"', api)
        self.assertIn('"computer.type"', api)
        self.assertIn('"computer.clipboard_read"', api)
        self.assertIn('"computer.launch_app"', api)
        self.assertIn('TryGetProperty("computer_control"', code)
        self.assertIn('ActionCountState.Text', code)
        self.assertNotIn('ExecutionSummary.Text', code)


if __name__ == "__main__":
    unittest.main()
