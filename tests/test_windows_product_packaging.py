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
        self.assertIn("ordax_chat_app.product_desktop", launcher)
        self.assertNotIn('L"ordax_studio.product_web_desktop"', launcher)
        self.assertNotIn('L"ordax_studio.web_desktop"', launcher)
        self.assertIn("ordax_device_agent.main", launcher)
        self.assertIn("ORDAX_AGENT_REPO_PATH", launcher)
        self.assertIn("ORDAX_BRIDGE_PATH", launcher)

    def test_launchers_expose_cooperative_shutdown_for_product_updates(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("ORDAXRuntimeShutdown", launcher)
        self.assertIn("ORDAXStudioShutdown", launcher)
        self.assertIn("CreateEventW", launcher)
        self.assertIn("WaitForMultipleObjects", launcher)
        self.assertIn("TerminateJobObject", launcher)
        self.assertIn("WaitForSingleObject(shutdown_event, backoff_ms)", launcher)

    def test_installer_stops_running_product_before_replacing_files(self) -> None:
        installer = (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(
            encoding="utf-8"
        )
        self.assertIn("function PrepareToInstall", installer)
        self.assertIn("SignalShutdownEvent", installer)
        self.assertIn("Local\\ORDAXRuntimeShutdown", installer)
        self.assertIn("Local\\ORDAXStudioShutdown", installer)
        self.assertIn("WaitForShutdownEventGone", installer)
        self.assertIn("taskkill.exe", installer)
        self.assertIn("0.3.0/0.3.1", installer)

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

    def test_product_shell_bundles_account_surface(self) -> None:
        product = (ROOT / "ordax_chat_app" / "app.html").read_text(encoding="utf-8")
        self.assertIn("Conta ORDAX", product)
        self.assertIn("ORDAX Web Bridge", product)
        self.assertIn("Agent / Responses", product)
        self.assertTrue((ROOT / "ordax_chat_app" / "product_desktop.py").is_file())
        self.assertTrue((ROOT / "ordax_studio" / "product_auth.py").is_file())

    def test_packaged_runtime_self_heals_only_existing_device_identity(self) -> None:
        entrypoint = (ROOT / "ordax_device_agent" / "main.py").read_text(encoding="utf-8")
        recovery = (ROOT / "ordax_dev_agent" / "device_identity_recovery.py").read_text(encoding="utf-8")
        self.assertIn("from ordax_dev_agent.main import main", entrypoint)
        self.assertIn("recover_existing_device_identity", entrypoint)
        self.assertIn("_recover_packaged_identity()", entrypoint)
        self.assertIn('if __name__ == "__main__":', entrypoint)
        self.assertIn('"operation": "identify"', recovery)
        self.assertNotIn('"operation": "enroll"', recovery)
        self.assertNotIn("github_token(", recovery)
        self.assertIn("machine-binding-mismatch", recovery)
        self.assertIn("credential-missing", recovery)

    def test_runtime_supervisor_is_not_bound_to_a_chat_client(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(
            encoding="utf-8"
        ).lower()
        self.assertNotIn("codex", launcher)
        self.assertNotIn("chatgpt", launcher)
        self.assertNotIn("claude", launcher)
        self.assertIn("ordaxruntime", launcher)

    def test_windows_ci_reinstalls_over_a_running_runtime(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-product-build.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("Upgrade over running ORDAX Runtime", workflow)
        self.assertIn('Wait-OrdaxReady -Label "ORDAX_UPGRADE_RUNTIME"', workflow)
        self.assertIn('Write-Host ($Label + "_STATE=" + $state)', workflow)
        self.assertIn("running runtime did not exit during upgrade", workflow)


if __name__ == "__main__":
    unittest.main()
