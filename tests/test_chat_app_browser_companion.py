from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from ordax_chat_app.browser_companion import BrowserCompanionServer, BrowserCompanionStore


class BrowserCompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        store = BrowserCompanionStore(Path(self.temp.name) / "companion.db")
        self.server = BrowserCompanionServer(store=store, port=0)
        self.server.start()
        self.addCleanup(self.server.stop)
        self.base = f"http://127.0.0.1:{self.server.port}"

    def request(self, path, *, method="GET", payload=None, token=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = {"content-type": "application/json", **(headers or {})}
        if token:
            request_headers["authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.base + path,
            data=body,
            method=method,
            headers=request_headers,
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read())

    def test_pair_observe_send_pull_ack_roundtrip(self):
        hello = self.request("/hello")
        self.assertEqual(hello["protocol"], 1)

        pairing = self.server.new_pairing_code()
        paired = self.request(
            "/pair",
            method="POST",
            payload={"code": pairing["code"], "browser_id": "browser-a"},
        )
        token = paired["token"]
        self.assertTrue(token)

        observed = self.request(
            "/events",
            method="POST",
            token=token,
            payload={
                "url": "https://chatgpt.com/c/conversation-12345678",
                "title": "ORDAX test",
                "browser_id": "browser-a",
                "messages": [
                    {"key": "u1", "role": "user", "text": "hello"},
                    {"key": "a1", "role": "assistant", "text": "hi"},
                ],
            },
        )
        self.assertEqual(observed["accepted"], 2)

        conversations = self.server.conversations()
        self.assertEqual(conversations[0]["id"], "conversation-12345678")
        self.assertEqual(len(self.server.messages("conversation-12345678")), 2)

        queued = self.server.send("conversation-12345678", "continue")
        pulled = self.request(
            "/commands",
            token=token,
            headers={"X-ORDAX-Conversation": "conversation-12345678"},
        )
        self.assertEqual(pulled["commands"][0]["id"], queued["id"])
        acked = self.request(
            "/commands/ack",
            method="POST",
            token=token,
            payload={"id": queued["id"], "ok": True},
        )
        self.assertEqual(acked["state"], "sent")

    def test_pairing_code_is_one_time_and_protected_routes_require_bearer(self):
        pairing = self.server.new_pairing_code()
        paired = self.request(
            "/pair",
            method="POST",
            payload={"code": pairing["code"], "browser_id": "browser-a"},
        )
        self.assertTrue(paired["token"])

        with self.assertRaises(urllib.error.HTTPError) as reused:
            self.request(
                "/pair",
                method="POST",
                payload={"code": pairing["code"], "browser_id": "browser-b"},
            )
        self.assertEqual(reused.exception.code, 403)

        with self.assertRaises(urllib.error.HTTPError) as unauthorized:
            self.request("/commands", headers={"X-ORDAX-Conversation": "anything"})
        self.assertEqual(unauthorized.exception.code, 401)

    def test_non_chatgpt_event_is_rejected(self):
        pairing = self.server.new_pairing_code()
        token = self.request(
            "/pair",
            method="POST",
            payload={"code": pairing["code"], "browser_id": "browser-a"},
        )["token"]
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            self.request(
                "/events",
                method="POST",
                token=token,
                payload={
                    "url": "https://example.com/c/not-chatgpt",
                    "messages": [],
                },
            )
        self.assertEqual(rejected.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
