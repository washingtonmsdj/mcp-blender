from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowsProductPackagingTests(unittest.TestCase):
    def test_native_launchers_are_product_entrypoints(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(encoding="utf-8")
        installer = (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(encoding="utf-8")
        self.assertIn("ORDAX Dev.exe", installer)
        self.assertIn("ORDAX Runtime.exe", installer)
        self.assertIn('L"%ls\\\\workbench\\\\ORDAX Workbench.exe"', launcher)
        self.assertIn("run_executable_child", launcher)
        self.assertNotIn('L"ordax_studio.product_web_desktop"', launcher)
        self.assertNotIn("ordax_chat_app", launcher)
        self.assertIn("ordax_device_agent.main", launcher)

    def test_launchers_expose_cooperative_shutdown_for_updates(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(encoding="utf-8")
        self.assertIn("ORDAXRuntimeShutdown", launcher)
        self.assertIn("ORDAXStudioShutdown", launcher)
        self.assertIn("CreateEventW", launcher)
        self.assertIn("WaitForMultipleObjects", launcher)
        self.assertIn("TerminateJobObject", launcher)

    def test_installer_is_host_only_and_has_no_chat_browser_bundle(self) -> None:
        installer = (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(encoding="utf-8").lower()
        build = (ROOT / "scripts" / "windows" / "build-ordax-studio-product.ps1").read_text(encoding="utf-8")
        self.assertNotIn("codex", installer)
        self.assertNotIn("browser_extension", build)
        self.assertNotIn("ordax_chat_app", build)
        self.assertIn("microsoftedgewebview2setup.exe", installer)
        self.assertIn("closeapplications=no", installer)
        self.assertIn("software\\microsoft\\windows\\currentversion\\run", installer)

    def test_installer_retires_legacy_scheduled_runtime_without_deleting_state(self) -> None:
        installer = (ROOT / "packaging" / "windows" / "ordax-studio.iss").read_text(encoding="utf-8")
        self.assertIn("RetireLegacyScheduledTask", installer)
        self.assertIn('/Query /TN "OrdaX Dev Agent"', installer)
        self.assertIn('/End /TN "OrdaX Dev Agent"', installer)
        self.assertIn('/Delete /F /TN "OrdaX Dev Agent"', installer)
        self.assertIn('{userstartup}\\OrdaX Dev Agent.lnk', installer)
        self.assertNotIn('filesandordirs; Name: "{localappdata}\\OrdaX\\DevAgent"', installer)

    def test_product_build_bundles_private_runtime(self) -> None:
        build = (ROOT / "scripts" / "windows" / "build-ordax-studio-product.ps1").read_text(encoding="utf-8")
        self.assertIn("python-$PythonVersion-embed-amd64.zip", build)
        self.assertIn("Lib\\site-packages", build)
        self.assertIn("pip install", build)
        self.assertIn("ORDAX_DEV_SETUP_SHA256", build)
        self.assertIn("dotnet publish", build)
        self.assertIn("ORDAX Workbench.exe", build)
        self.assertIn("--self-contained true", build)

    def test_product_shell_is_project_host_not_embedded_chat(self) -> None:
        product = (ROOT / "ordax_studio" / "studio_product.html").read_text(encoding="utf-8")
        script = (ROOT / "ordax_studio" / "assets" / "studio.js").read_text(encoding="utf-8")
        self.assertIn("ORDAX Dev", product)
        self.assertIn("Visão geral", product)
        self.assertIn("MCP", product)
        self.assertNotIn("Agent / Responses", product)
        self.assertNotIn("Browser Companion", product)
        self.assertNotIn("Chat normal", product)
        self.assertNotIn("agentPrompt", script)

    def test_native_workbench_is_provider_neutral_and_uses_webview2(self) -> None:
        project = (ROOT / "native" / "ordax-workbench" / "Ordax.Workbench.csproj").read_text(encoding="utf-8")
        xaml = (ROOT / "native" / "ordax-workbench" / "MainWindow.xaml").read_text(encoding="utf-8")
        code = (ROOT / "native" / "ordax-workbench" / "MainWindow.xaml.cs").read_text(encoding="utf-8")
        bridge = (ROOT / "ordax_studio" / "workbench_bridge.py").read_text(encoding="utf-8")
        studio_js = (ROOT / "ordax_studio" / "assets" / "studio.js").read_text(encoding="utf-8")

        self.assertIn("Microsoft.Web.WebView2", project)
        self.assertIn("WebView2CompositionControl", xaml)
        self.assertIn('x:Name="ProviderView"', xaml)
        self.assertIn('x:Name="PreviewView"', xaml)
        self.assertIn('x:Name="WorkbenchBrowserView"', xaml)
        self.assertIn('Header="Execuções"', xaml)
        self.assertIn("StudioView.CoreWebView2.WebMessageReceived", code)
        self.assertIn("ProviderView.CoreWebView2.WebMessageReceived", code)
        self.assertIn('"provider.ordax.local"', code)
        self.assertIn('method is not ("provider_api_models" or "provider_api_chat")', code)
        self.assertIn("_ALLOWED_METHODS", bridge)
        provider = (ROOT / "ordax_studio" / "provider_api.html").read_text(encoding="utf-8")
        self.assertIn("ordax-provider-rpc", provider)
        self.assertNotIn("api_key", provider.lower())
        self.assertIn("window.chrome?.webview", studio_js)
        self.assertIn("window.pywebview?.api?.[name]", studio_js)

    def test_runtime_supervisor_is_client_neutral(self) -> None:
        launcher = (ROOT / "packaging" / "windows" / "ordax_launcher.c").read_text(encoding="utf-8").lower()
        self.assertNotIn("codex", launcher)
        self.assertNotIn("chatgpt", launcher)
        self.assertNotIn("claude", launcher)
        self.assertIn("ordaxruntime", launcher)

    def test_windows_ci_reinstalls_over_running_runtime(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-product-build.yml").read_text(encoding="utf-8")
        self.assertIn("Upgrade over running ORDAX Runtime", workflow)
        self.assertIn('Wait-OrdaxReady -Label "ORDAX_UPGRADE_RUNTIME"', workflow)
        self.assertIn("running runtime did not exit during upgrade", workflow)
        self.assertIn("LEGACY_ORDAX_TASK_REMOVED", workflow)
        self.assertIn("LEGACY_ORDAX_STARTUP_REMOVED", workflow)
        self.assertIn("ORDAX_WORKBENCH_READY", workflow)
        self.assertIn("workbench\\ORDAX Workbench.exe", workflow)


if __name__ == "__main__":
    unittest.main()
