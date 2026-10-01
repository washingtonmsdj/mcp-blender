from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ordax_chat_app.managed_chat_browser import ManagedChatBrowser


class ManagedChatBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.extension = self.root / "extension"
        self.extension.mkdir()
        (self.extension / "manifest.json").write_text("{}", encoding="utf-8")
        self.browser = self.root / "chrome.exe"
        self.browser.write_text("", encoding="utf-8")

    def test_start_uses_dedicated_persistent_profile_and_extension(self):
        process = Mock()
        process.pid = 123
        process.poll.return_value = None
        with patch("ordax_chat_app.managed_chat_browser.subprocess.Popen", return_value=process) as popen:
            manager = ManagedChatBrowser(
                extension_dir=self.extension,
                state_dir=self.root / "state",
                browser_path=self.browser,
            )
            status = manager.start()
        self.assertTrue(status["running"])
        args = popen.call_args.args[0]
        self.assertIn(f"--user-data-dir={manager.profile_dir}", args)
        self.assertIn(f"--load-extension={self.extension}", args)
        self.assertIn(f"--disable-extensions-except={self.extension}", args)
        self.assertIn("--app=https://chatgpt.com/", args)
        self.assertNotIn("--remote-debugging-port", " ".join(args))

    def test_missing_extension_fails_before_browser_launch(self):
        manager = ManagedChatBrowser(
            extension_dir=self.root / "missing",
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        with self.assertRaisesRegex(RuntimeError, "extension is missing"):
            manager.start()

    def test_status_does_not_require_process(self):
        manager = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        status = manager.status()
        self.assertFalse(status["running"])
        self.assertTrue(status["extension_available"])
        self.assertEqual(status["browser"], str(self.browser.resolve()))


if __name__ == "__main__":
    unittest.main()
