from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
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

    def test_download_url_must_use_official_chrome_for_testing_origin(self):
        managed = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        accepted = managed._validate_download_url(
            "https://storage.googleapis.com/chrome-for-testing-public/153.0.0.0/win64/chrome-win64.zip"
        )
        self.assertTrue(accepted.startswith("https://storage.googleapis.com/"))
        with self.assertRaisesRegex(RuntimeError, "Unexpected Chrome for Testing"):
            managed._validate_download_url("https://example.com/chrome.zip")

    def test_install_browser_extracts_private_runtime_and_persists_metadata(self):
        managed = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
        )

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("chrome-win64/chrome.exe", b"signed-stub")
            bundle.writestr("chrome-win64/resources.pak", b"resource")
        archive_bytes = archive.getvalue()

        metadata = {
            "channels": {
                "Stable": {
                    "version": "153.0.8010.52",
                    "downloads": {
                        "chrome": [
                            {
                                "platform": "win64",
                                "url": "https://storage.googleapis.com/chrome-for-testing-public/153.0.8010.52/win64/chrome-win64.zip",
                            }
                        ]
                    },
                }
            }
        }

        class Response:
            def __init__(self, data):
                self._data = data
                self._stream = io.BytesIO(data)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                return self._stream.read(size)

        calls = []

        def fake_urlopen(request, timeout=None):
            url = request.full_url
            calls.append(url)
            if url.endswith("last-known-good-versions-with-downloads.json"):
                return Response(json.dumps(metadata).encode("utf-8"))
            return Response(archive_bytes)

        with patch(
            "ordax_chat_app.managed_chat_browser.urllib.request.urlopen",
            side_effect=fake_urlopen,
        ), patch.object(
            ManagedChatBrowser,
            "_verify_windows_signature",
            return_value={
                "status": "Valid",
                "subject": "CN=Google LLC",
                "product_version": "153.0.8010.52",
            },
        ), patch.object(
            ManagedChatBrowser,
            "_is_windows",
            return_value=True,
        ):
            result = managed.install_browser()

        private = managed.browser_dir / "chrome-win64" / "chrome.exe"
        self.assertTrue(private.is_file())
        self.assertTrue(result["managed_runtime_installed"])
        stored = json.loads(managed.browser_metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["version"], "153.0.8010.52")
        self.assertEqual(len(calls), 2)

    def test_windows_signature_rejects_hash_mismatch(self):
        managed = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        payload = {
            "Status": "HashMismatch",
            "Subject": "CN=Google LLC",
            "ProductVersion": "153.0.8010.52",
        }
        result = Mock()
        result.returncode = 0
        result.stdout = json.dumps(payload)
        result.stderr = ""
        with patch.object(
            ManagedChatBrowser,
            "_is_windows",
            return_value=True,
        ), patch(
            "ordax_chat_app.managed_chat_browser.subprocess.run",
            return_value=result,
        ):
            with self.assertRaisesRegex(RuntimeError, "signature is invalid"):
                managed._verify_windows_signature(
                    self.browser,
                    expected_version="153.0.8010.52",
                )

    def test_windows_signature_accepts_google_unknown_chain_when_version_matches(self):
        managed = ManagedChatBrowser(
            extension_dir=self.extension,
            state_dir=self.root / "state",
            browser_path=self.browser,
        )
        payload = {
            "Status": "UnknownError",
            "Subject": "CN=Google LLC, O=Google LLC",
            "ProductVersion": "153.0.8010.52",
        }
        result = Mock()
        result.returncode = 0
        result.stdout = json.dumps(payload)
        result.stderr = ""
        with patch.object(
            ManagedChatBrowser,
            "_is_windows",
            return_value=True,
        ), patch(
            "ordax_chat_app.managed_chat_browser.subprocess.run",
            return_value=result,
        ):
            signature = managed._verify_windows_signature(
                self.browser,
                expected_version="153.0.8010.52",
            )
        self.assertEqual(signature["status"], "UnknownError")
        self.assertIn("Google", signature["subject"])

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
