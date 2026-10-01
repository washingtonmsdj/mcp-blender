from __future__ import annotations

import unittest
from pathlib import Path

import ordax_chat_app


class ChatAppPackageTests(unittest.TestCase):
    def test_desktop_assets_exist_next_to_package(self):
        root = Path(ordax_chat_app.__file__).resolve().parent
        self.assertTrue((root / "app.html").is_file())
        self.assertTrue((root / "assets" / "app.css").is_file())
        self.assertTrue((root / "assets" / "app.js").is_file())


if __name__ == "__main__":
    unittest.main()
