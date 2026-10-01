from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ordax_chat_app.policy import CapabilityPolicyStore


class CapabilityPolicyStoreTests(unittest.TestCase):
    def test_sensitive_capabilities_default_denied_and_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "state.db"
            store = CapabilityPolicyStore(db)
            self.assertFalse(store.enabled("demo", "computer.observe"))
            self.assertFalse(store.enabled("demo", "computer.interact"))

            store.set("demo", "computer.observe", True)
            reopened = CapabilityPolicyStore(db)
            self.assertTrue(reopened.enabled("demo", "computer.observe"))
            self.assertFalse(reopened.enabled("demo", "computer.interact"))
            self.assertEqual(
                reopened.project("demo"),
                {
                    "computer.interact": False,
                    "computer.observe": True,
                },
            )

    def test_capabilities_are_project_scoped_and_unknown_names_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CapabilityPolicyStore(Path(directory) / "state.db")
            store.set("first", "computer.interact", True)
            self.assertTrue(store.enabled("first", "computer.interact"))
            self.assertFalse(store.enabled("second", "computer.interact"))
            with self.assertRaisesRegex(ValueError, "unknown capability"):
                store.set("first", "computer.everything", True)


if __name__ == "__main__":
    unittest.main()
