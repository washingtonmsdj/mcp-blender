from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowsProductPackagingTests(unittest.TestCase):
    def test_native_launchers_are_product_entrypoints(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("ORDAX Studio.exe", (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(encoding="utf-8"))
        self.assertIn("ORDAX Runtime.exe", (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(encoding="utf-8"))
        self.assertIn("ordax_studio.web_desktop", launcher)
        self.assertIn("ordax_device_agent.main", launcher)
        self.assertIn("ORDAX_AGENT_REPO_PATH", launcher)
        self.assertIn("ORDAX_BRIDGE_PATH", launcher)

    def test_installer_does_not_expose_python_or_codex_as_user_dependency(self) -> None:
        installer = (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(
            encoding="utf-8"
        ).lower()
        self.assertNotIn("pythonw.exe", installer)
        self.assertNotIn("codex", installer)
        self.assertIn("software\\microsoft\\windows\\currentversion\\run", installer)
        self.assertIn("microsoftedgewebview2setup.exe", installer)

    def test_product_build_bundles_private_runtime_and_project_scripts(self) -> None:
        build = (ROOT / "scripts" / "windows" / "build-ordax-studio-product.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("python-$PythonVersion-embed-amd64.zip", build)
        self.assertIn("Lib\\site-packages", build)
        self.assertIn("pip install", build)
        self.assertIn('Copy-Item (Join-Path $repoRoot "scripts")', build)
        self.assertIn("ORDAX_STUDIO_SETUP_SHA256", build)

    def test_runtime_supervisor_is_not_bound_to_a_chat_client(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(
            encoding="utf-8"
        ).lower()
        self.assertNotIn("codex", launcher)
        self.assertNotIn("chatgpt", launcher)
        self.assertNotIn("claude", launcher)
        self.assertIn("ordaxruntime", launcher)


if __name__ == "__main__":
    unittest.main()
