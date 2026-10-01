"""OpenAI ChatGPT-plan provider for the ORDAX desktop app.

This adapter follows the Sign in with ChatGPT open-source inference contract:
OAuth bearer token, public /v1/responses endpoint, store=false and stream=true.
Credential acquisition/refresh is owned by the account layer; this provider only
receives a short-lived access token through token_provider.
"""
from __future__ import annotations

import json
from typing import Any, Callable

import httpx

from .base import ChatDeltaHandler, ChatModel, ChatTurnResult


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class OpenAIChatGPTPlanProvider:
    def __init__(
        self,
        token_provider: Callable[[], str],
        *,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.token_provider = token_provider
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _token(self) -> str:
        token = str(self.token_provider() or "").strip()
        if not token:
            raise ProviderError("ChatGPT access token is unavailable", code="token_missing")
        return token

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._token()}",
            "content-type": "application/json",
            "accept": "text/event-stream",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
            follow_redirects=False,
        )

    def list_models(self) -> list[ChatModel]:
        headers = {"authorization": f"Bearer {self._token()}"}
        with self._client() as client:
            response = client.get(f"{self.base_url}/models", headers=headers)
        if not response.is_success:
            raise self._http_error(response, "model catalog request failed")
        payload = response.json()
        raw_models = payload.get("models")
        if raw_models is None:
            raw_models = payload.get("data", [])
        if not isinstance(raw_models, list):
            raise ProviderError("model catalog response is invalid", code="invalid_model_catalog")
        models: list[ChatModel] = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            if item.get("visibility") not in (None, "list"):
                continue
            slug = str(item.get("slug") or item.get("id") or "").strip()
            if not slug:
                continue
            display = str(item.get("display_name") or item.get("name") or slug).strip()
            models.append(ChatModel(slug, display))
        return models

    def run_turn(
        self,
        *,
        model: str,
        input_items: list[dict[str, Any]],
        instructions: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        on_delta: ChatDeltaHandler | None = None,
    ) -> ChatTurnResult:
        model = model.strip()
        if not model:
            raise ValueError("model is required")
        if not isinstance(input_items, list) or not input_items:
            raise ValueError("input_items must be a non-empty list")

        body: dict[str, Any] = {
            "model": model,
            "input": input_items,
            "store": False,
            "stream": True,
        }
        if instructions:
            body["instructions"] = instructions
        if tools:
            body["tools"] = tools

        text_parts: list[str] = []
        completed_event: dict[str, Any] | None = None
        completed = False

        with self._client() as client:
            with client.stream(
                "POST",
                f"{self.base_url}/responses",
                headers=self._headers(),
                json=body,
            ) as response:
                if not response.is_success:
                    response.read()
                    raise self._http_error(response, "Responses request failed")

                for line in response.iter_lines():
                    line = line.strip()
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError as error:
                        raise ProviderError(
                            f"Responses stream contained invalid JSON: {error}",
                            code="invalid_stream_event",
                        ) from error
                    if not isinstance(event, dict):
                        continue
                    event_type = str(event.get("type") or "")
                    if event_type == "response.output_text.delta":
                        delta = str(event.get("delta") or "")
                        if delta:
                            text_parts.append(delta)
                            if on_delta is not None:
                                on_delta(delta)
                    elif event_type == "response.failed":
                        response_obj = event.get("response")
                        error_obj = response_obj.get("error") if isinstance(response_obj, dict) else None
                        code = str(error_obj.get("code") or "response_failed") if isinstance(error_obj, dict) else "response_failed"
                        message = str(error_obj.get("message") or code) if isinstance(error_obj, dict) else code
                        raise ProviderError(message, code=code)
                    elif event_type == "response.incomplete":
                        raise ProviderError("Response ended incomplete", code="response_incomplete")
                    elif event_type == "response.completed":
                        completed = True
                        completed_event = event

        if not completed or completed_event is None:
            raise ProviderError(
                "Responses stream ended without response.completed",
                code="stream_ended_without_completed",
            )

        response_obj = completed_event.get("response")
        response_id = None
        usage: dict[str, Any] = {}
        if isinstance(response_obj, dict):
            response_id = str(response_obj.get("id") or "") or None
            if isinstance(response_obj.get("usage"), dict):
                usage = dict(response_obj["usage"])
        return ChatTurnResult(
            text="".join(text_parts),
            response_id=response_id,
            usage=usage,
            raw_completed_event=completed_event,
        )

    @staticmethod
    def _http_error(response: httpx.Response, prefix: str) -> ProviderError:
        code = None
        detail = ""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    code = str(error.get("code") or "") or None
                    detail = str(error.get("message") or "")
                elif isinstance(error, str):
                    detail = error
        except (ValueError, json.JSONDecodeError):
            detail = response.text[-2000:]
        message = prefix
        if detail:
            message += f": {detail}"
        return ProviderError(message, code=code, status_code=response.status_code)
