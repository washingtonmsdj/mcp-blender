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
        self.extension = self.root / "browser_extension"
        self.extension.mkdir()
        (self.extension / "manifest.json").write_text("{}", encoding="utf-8")
        self.browser = self.root / "chrome.exe"
        self.browser.write_bytes(b"stub")

    def test_start_uses_persistent_profile_and_companion_extension(self):
        fake_process = Mock()
        fake_process.pid = 1234
        fake_process.poll.return_value = None

        managed = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        with patch(
            "ordax_chat_app.managed_chat_browser.subprocess.Popen",
            return_value=fake_process,
        ) as popen:
            status = managed.start(
                initial_url="http://127.0.0.1:8775/bootstrap?code=12345678"
            )

        args = popen.call_args.args[0]
        self.assertIn(f"--user-data-dir={managed.profile_dir}", args)
        self.assertIn(f"--disable-extensions-except={self.extension.resolve()}", args)
        self.assertIn(f"--load-extension={self.extension.resolve()}", args)
        self.assertIn(
            "--app=http://127.0.0.1:8775/bootstrap?code=12345678",
            args,
        )
        self.assertTrue(status["running"])
        self.assertEqual(status["profile_dir"], str(managed.profile_dir))
        self.assertTrue(managed.profile_dir.is_dir())

    def test_profile_directory_is_stable_across_instances(self):
        state = self.root / "state"
        first = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=state,
            browser_path=self.browser,
        )
        second = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=state,
            browser_path=self.browser,
        )
        self.assertEqual(first.profile_dir, second.profile_dir)

    def test_untrusted_initial_url_is_rejected(self):
        managed = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        with self.assertRaisesRegex(ValueError, "unsupported managed ChatGPT browser"):
            managed.start(initial_url="https://example.com/")


if __name__ == "__main__":
    unittest.main()
