from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from ordax_studio.product_web_desktop import (
    StudioProductApi,
    _openai_compatible_base_url,
    _provider_headers,
)


class WorkbenchProviderApiTests(unittest.TestCase):
    def setUp(self):
        self.api = object.__new__(StudioProductApi)

    def test_base_url_accepts_openai_compatible_http_and_rejects_embedded_credentials(self):
        self.assertEqual(
            "http://localhost:1234/v1",
            _openai_compatible_base_url("http://localhost:1234/v1/"),
        )
        self.assertEqual(
            "https://api.example.test/v1",
            _openai_compatible_base_url("https://api.example.test/v1"),
        )
        with self.assertRaises(ValueError):
            _openai_compatible_base_url("https://user:secret@example.test/v1")
        with self.assertRaises(ValueError):
            _openai_compatible_base_url("file:///tmp/provider")

    def test_api_key_is_read_only_from_named_environment_variable(self):
        with patch.dict(os.environ, {"ORDAX_TEST_PROVIDER_KEY": "secret-value"}, clear=False):
            headers = _provider_headers("ORDAX_TEST_PROVIDER_KEY")
        self.assertEqual("Bearer secret-value", headers["authorization"])
        with self.assertRaises(ValueError):
            _provider_headers("INVALID-NAME")

    def test_models_uses_openai_compatible_models_endpoint_without_returning_key(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [
                {"id": "local/model-a", "owned_by": "local"},
                {"id": "local/model-b"},
            ]
        }
        with (
            patch.dict(os.environ, {"ORDAX_TEST_PROVIDER_KEY": "secret-value"}, clear=False),
            patch("ordax_studio.product_web_desktop.httpx.get", return_value=response) as get,
        ):
            result = self.api.provider_api_models(
                "http://localhost:1234/v1",
                "ORDAX_TEST_PROVIDER_KEY",
            )

        self.assertTrue(result["ok"], result.get("summary"))
        self.assertEqual(["local/model-a", "local/model-b"], [
            item["id"] for item in result["data"]["models"]
        ])
        self.assertNotIn("secret-value", repr(result))
        args, kwargs = get.call_args
        self.assertEqual("http://localhost:1234/v1/models", args[0])
        self.assertEqual("Bearer secret-value", kwargs["headers"]["authorization"])
        self.assertFalse(kwargs["follow_redirects"])

    def test_chat_posts_bounded_text_messages_and_returns_text_content(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "model": "local/model-a",
            "choices": [{
                "message": {"role": "assistant", "content": "Resposta local"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 3,
                "total_tokens": 8,
            },
        }
        with patch(
            "ordax_studio.product_web_desktop.httpx.post",
            return_value=response,
        ) as post:
            result = self.api.provider_api_chat(
                "http://localhost:1234/v1",
                "local/model-a",
                [{"role": "user", "content": "Olá"}],
            )

        self.assertTrue(result["ok"], result.get("summary"))
        self.assertEqual("Resposta local", result["data"]["content"])
        self.assertEqual(8, result["data"]["usage"]["total_tokens"])
        args, kwargs = post.call_args
        self.assertEqual("http://localhost:1234/v1/chat/completions", args[0])
        self.assertEqual("local/model-a", kwargs["json"]["model"])
        self.assertEqual(
            [{"role": "user", "content": "Olá"}],
            kwargs["json"]["messages"],
        )
        self.assertFalse(kwargs["json"]["stream"])
        self.assertFalse(kwargs["follow_redirects"])

    def test_chat_rejects_non_text_or_oversized_contracts_before_network(self):
        with patch("ordax_studio.product_web_desktop.httpx.post") as post:
            invalid = self.api.provider_api_chat(
                "http://localhost:1234/v1",
                "model",
                [{"role": "tool", "content": "x"}],
            )
            too_many = self.api.provider_api_chat(
                "http://localhost:1234/v1",
                "model",
                [{"role": "user", "content": "x"}] * 101,
            )
        self.assertFalse(invalid["ok"])
        self.assertFalse(too_many["ok"])
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
