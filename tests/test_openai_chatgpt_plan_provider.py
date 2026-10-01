from __future__ import annotations

import json
import unittest

import httpx

from ordax_chat_app.providers import OpenAIChatGPTPlanProvider, ProviderError


def sse(*events: dict) -> bytes:
    return "".join(f"data: {json.dumps(event)}\n\n" for event in events).encode("utf-8")


class OpenAIChatGPTPlanProviderTests(unittest.TestCase):
    def test_model_catalog_uses_account_visible_models(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/v1/models")
            self.assertEqual(request.headers["authorization"], "Bearer token")
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"slug": "gpt-visible", "display_name": "Visible", "visibility": "list"},
                        {"slug": "gpt-hidden", "display_name": "Hidden", "visibility": "hidden"},
                    ]
                },
            )

        provider = OpenAIChatGPTPlanProvider(
            lambda: "token",
            transport=httpx.MockTransport(handler),
        )
        models = provider.list_models()
        self.assertEqual([(m.id, m.display_name) for m in models], [("gpt-visible", "Visible")])

    def test_responses_turn_is_streamed_store_false_and_completed(self) -> None:
        deltas: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/v1/responses")
            body = json.loads(request.content)
            self.assertFalse(body["store"])
            self.assertTrue(body["stream"])
            self.assertEqual(body["include"], ["reasoning.encrypted_content"])
            self.assertEqual(body["model"], "gpt-test")
            self.assertEqual(body["input"][0]["content"], "hello")
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=sse(
                    {"type": "response.output_text.delta", "delta": "Hello"},
                    {"type": "response.output_text.delta", "delta": "!"},
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_123",
                            "usage": {"input_tokens": 10, "output_tokens": 2},
                        },
                    },
                ),
            )

        provider = OpenAIChatGPTPlanProvider(
            lambda: "token",
            transport=httpx.MockTransport(handler),
        )
        result = provider.run_turn(
            model="gpt-test",
            input_items=[{"role": "user", "content": "hello"}],
            on_delta=deltas.append,
        )
        self.assertEqual(result.text, "Hello!")
        self.assertEqual(result.response_id, "resp_123")
        self.assertEqual(result.usage["input_tokens"], 10)
        self.assertEqual(deltas, ["Hello", "!"])

    def test_failed_stream_preserves_machine_readable_code(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=sse(
                    {
                        "type": "response.failed",
                        "response": {
                            "error": {
                                "code": "subscription_sharing_usage_limit_exceeded",
                                "message": "limit reached",
                            }
                        },
                    }
                ),
            )

        provider = OpenAIChatGPTPlanProvider(
            lambda: "token",
            transport=httpx.MockTransport(handler),
        )
        with self.assertRaises(ProviderError) as raised:
            provider.run_turn(
                model="gpt-test",
                input_items=[{"role": "user", "content": "hello"}],
            )
        self.assertEqual(
            raised.exception.code,
            "subscription_sharing_usage_limit_exceeded",
        )

    def test_missing_token_fails_before_network(self) -> None:
        provider = OpenAIChatGPTPlanProvider(lambda: "")
        with self.assertRaisesRegex(ProviderError, "token is unavailable"):
            provider.list_models()


if __name__ == "__main__":
    unittest.main()
