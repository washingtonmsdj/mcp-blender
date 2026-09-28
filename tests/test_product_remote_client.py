from __future__ import annotations

import json
import unittest

import httpx

from ordax_dev_agent.product_remote_client import (
    ProductRemoteClient,
    ProductRemoteError,
)


class ProductRemoteClientTests(unittest.TestCase):
    def test_session_targets_and_action_flow_do_not_store_token(self):
        seen: list[tuple[str, str, str]] = []
        polls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((
                request.method,
                request.url.path,
                request.headers.get("authorization", ""),
            ))
            if request.url.path == "/v3/product/session":
                return httpx.Response(200, json={
                    "ok": True,
                    "session": {"subject_id": "user:1"},
                })
            if request.url.path == "/v3/product/targets":
                return httpx.Response(200, json={
                    "ok": True,
                    "targets": [{"device_id": "dev-1", "name": "Workstation", "grants": []}],
                })
            if request.url.path == "/v3/product/actions" and request.method == "POST":
                body = json.loads(request.content.decode("utf-8"))
                self.assertEqual(body["device_id"], "dev-1")
                self.assertEqual(body["action"], "git.status")
                self.assertEqual(body["project"], "demo")
                return httpx.Response(202, json={
                    "ok": True,
                    "request_id": "req-1",
                    "status": "queued",
                })
            if request.url.path == "/v3/product/actions/req-1":
                polls["count"] += 1
                status = "running" if polls["count"] == 1 else "succeeded"
                return httpx.Response(200, json={
                    "ok": True,
                    "action": {
                        "request_id": "req-1",
                        "status": status,
                        "result": {"ok": True},
                    },
                })
            return httpx.Response(404, json={"ok": False, "error": "not_found"})

        http = httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://unused.test",
        )
        client = ProductRemoteClient("https://control.example.test", http=http)

        self.assertEqual(client.session("jwt-one")["subject_id"], "user:1")
        self.assertEqual(client.targets("jwt-two")[0]["device_id"], "dev-1")
        request_id = client.submit_action(
            "jwt-three",
            device_id="dev-1",
            action="git.status",
            project="demo",
            arguments={"project": "demo"},
        )
        self.assertEqual(request_id, "req-1")
        result = client.wait_action(
            "jwt-four",
            request_id,
            timeout_seconds=2,
            poll_interval_seconds=0.1,
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertFalse(hasattr(client, "access_token"))
        self.assertEqual(
            [authorization for _, _, authorization in seen],
            [
                "Bearer jwt-one",
                "Bearer jwt-two",
                "Bearer jwt-three",
                "Bearer jwt-four",
                "Bearer jwt-four",
            ],
        )

    def test_control_plane_errors_are_typed(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={"ok": False, "error": "product_grant_not_resolved"},
            )

        client = ProductRemoteClient(
            "https://control.example.test",
            http=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with self.assertRaises(ProductRemoteError) as caught:
            client.targets("jwt")
        self.assertEqual(caught.exception.error_code, "product_grant_not_resolved")
        self.assertEqual(caught.exception.status_code, 403)

    def test_requires_https_and_bounded_wait_parameters(self):
        with self.assertRaises(ValueError):
            ProductRemoteClient("http://control.example.test")

        client = ProductRemoteClient(
            "https://control.example.test",
            http=httpx.Client(transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={"ok": True, "action": {"status": "queued"}})
            )),
        )
        with self.assertRaises(ValueError):
            client.wait_action("jwt", "req", timeout_seconds=0)
        with self.assertRaises(ValueError):
            client.wait_action("jwt", "req", poll_interval_seconds=0.01)


if __name__ == "__main__":
    unittest.main()
