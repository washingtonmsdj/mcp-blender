from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkbenchComputerFirstUiTests(unittest.TestCase):
    def test_workbench_is_computer_first(self) -> None:
        xaml = (ROOT / "native" / "ordax-workbench" / "MainWindow.xaml").read_text(encoding="utf-8")
        self.assertIn('Title="ORDAX Studio"', xaml)
        self.assertIn('Header="Visão geral"', xaml)
        self.assertIn('x:Name="ComputerControlState"', xaml)
        self.assertIn('x:Name="ComputerRailState"', xaml)
        self.assertIn('x:Name="DeviceCardState"', xaml)
        self.assertIn('x:Name="McpCardState"', xaml)
        self.assertIn('Text="Acesso remoto com grants"', xaml)
        self.assertIn('Text="Blender · Unity"', xaml)
        self.assertIn('Header="Web IA"', xaml)
        self.assertIn('x:Name="ProviderView"', xaml)

    def test_status_surface_uses_real_computer_control_contract(self) -> None:
        api = (ROOT / "ordax_studio" / "web_desktop.py").read_text(encoding="utf-8")
        code = (ROOT / "native" / "ordax-workbench" / "MainWindow.xaml.cs").read_text(encoding="utf-8")
        self.assertIn('"computer_control": computer_control', api)
        self.assertIn('"computer.screenshot"', api)
        self.assertIn('"computer.type_text"', api)
        self.assertIn('"computer.clipboard_read"', api)
        self.assertIn('"computer.launch_app"', api)
        self.assertIn('TryGetProperty("computer_control"', code)
        self.assertIn('ActionCountState.Text', code)
        self.assertNotIn('ExecutionSummary.Text', code)


if __name__ == "__main__":
    unittest.main()
