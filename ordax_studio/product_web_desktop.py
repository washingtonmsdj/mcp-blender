from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig

from .blender_connection import prepare_blender_connection
from .instance_lock import SingleInstanceLock
from .product_auth import ProductAccountError, connect_existing_device
from .web_desktop import APP_NAME, StudioApi


_API_KEY_ENV_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")


def _openai_compatible_base_url(raw: str) -> str:
    value = str(raw or "").strip().rstrip("/")
    if not value or len(value) > 2048:
        raise ValueError("Base URL da API é obrigatória e deve ter no máximo 2048 caracteres")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Base URL deve usar http:// ou https://")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credenciais não podem ficar embutidas na URL")
    path = (parsed.path or "").rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _provider_headers(api_key_env: str) -> dict[str, str]:
    name = str(api_key_env or "").strip()
    headers = {"content-type": "application/json", "accept": "application/json"}
    if not name:
        return headers
    if not _API_KEY_ENV_RE.fullmatch(name):
        raise ValueError("Nome da variável de ambiente da API key é inválido")
    key = str(os.environ.get(name) or "").strip()
    if not key:
        raise ValueError(f"Variável de ambiente não configurada: {name}")
    headers["authorization"] = f"Bearer {key}"
    return headers


class StudioProductApi(StudioApi):
    """Windows product surface layered over the canonical Studio API.

    The base Studio API remains provider-neutral. Account authentication,
    device ownership and interactive desktop lifecycle operations live here so
    development hosts do not need to own or store Product credentials.
    """

    def provider_api_models(
        self,
        base_url: str,
        api_key_env: str = "",
    ) -> dict[str, Any]:
        try:
            base = _openai_compatible_base_url(base_url)
            response = httpx.get(
                f"{base}/models",
                headers=_provider_headers(api_key_env),
                timeout=15.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            raw_models = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(raw_models, list):
                raise ValueError("Resposta /models não contém data[]")
            models: list[dict[str, Any]] = []
            for item in raw_models[:500]:
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("id") or "").strip()
                if not model_id or len(model_id) > 500:
                    continue
                models.append({
                    "id": model_id,
                    "owned_by": str(item.get("owned_by") or "")[:200],
                })
            return {
                "ok": True,
                "summary": f"{len(models)} modelo(s) disponível(is)",
                "data": {"models": models, "base_url": base},
            }
        except (ValueError, httpx.HTTPError) as error:
            return {
                "ok": False,
                "summary": f"API compatível indisponível: {type(error).__name__}: {error}",
            }

    def provider_api_chat(
        self,
        base_url: str,
        model: str,
        messages: list[dict[str, Any]],
        api_key_env: str = "",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        try:
            base = _openai_compatible_base_url(base_url)
            selected_model = str(model or "").strip()
            if not selected_model or len(selected_model) > 500:
                raise ValueError("Modelo é obrigatório")
            if not isinstance(messages, list) or not 1 <= len(messages) <= 100:
                raise ValueError("messages deve conter entre 1 e 100 mensagens")

            sanitized: list[dict[str, str]] = []
            total_chars = 0
            for item in messages:
                if not isinstance(item, dict):
                    raise ValueError("Cada mensagem deve ser um objeto")
                role = str(item.get("role") or "").strip().lower()
                content = item.get("content")
                if role not in {"system", "user", "assistant"} or not isinstance(content, str):
                    raise ValueError("Mensagens aceitam apenas role system/user/assistant e conteúdo textual")
                if len(content) > 100_000:
                    raise ValueError("Uma mensagem excede 100000 caracteres")
                total_chars += len(content)
                if total_chars > 250_000:
                    raise ValueError("Histórico da conversa excede 250000 caracteres")
                sanitized.append({"role": role, "content": content})

            try:
                temp = float(temperature)
            except (TypeError, ValueError) as error:
                raise ValueError("temperature deve ser numérico") from error
            if not 0.0 <= temp <= 2.0:
                raise ValueError("temperature deve ficar entre 0 e 2")
            if isinstance(max_tokens, bool):
                raise ValueError("max_tokens deve ser inteiro")
            tokens = int(max_tokens)
            if not 1 <= tokens <= 32768:
                raise ValueError("max_tokens deve ficar entre 1 e 32768")

            response = httpx.post(
                f"{base}/chat/completions",
                headers=_provider_headers(api_key_env),
                json={
                    "model": selected_model,
                    "messages": sanitized,
                    "temperature": temp,
                    "max_tokens": tokens,
                    "stream": False,
                },
                timeout=180.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices") if isinstance(payload, dict) else None
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise ValueError("Resposta de chat não contém choices[0]")
            message = choices[0].get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError("Resposta de chat não contém message.content textual")
            content = str(message["content"])
            usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
            return {
                "ok": True,
                "summary": "Resposta recebida do provider",
                "data": {
                    "model": str(payload.get("model") or selected_model)[:500],
                    "content": content,
                    "finish_reason": str(choices[0].get("finish_reason") or "")[:100],
                    "usage": {
                        key: usage.get(key)
                        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                        if isinstance(usage.get(key), int)
                    },
                    "base_url": base,
                },
            }
        except (ValueError, httpx.HTTPError, TypeError) as error:
            return {
                "ok": False,
                "summary": f"Falha no provider API: {type(error).__name__}: {error}",
            }

    def connect_product_account(self, email: str, password: str) -> dict[str, Any]:
        try:
            data = connect_existing_device(self.agent.config, email, password)
        except ProductAccountError as error:
            return {
                "ok": False,
                "code": error.code,
                "summary": error.message,
            }
        except Exception as error:
            return {
                "ok": False,
                "code": "product_account_unexpected_error",
                "summary": f"{type(error).__name__}: não foi possível conectar a conta ORDAX",
            }
        return {
            "ok": True,
            "summary": "Conta ORDAX conectada a este computador",
            "data": data,
        }

    def blender_prepare(self) -> dict[str, Any]:
        return prepare_blender_connection(self.agent, self.project, wait_seconds=4.0)

    def blender_install_bridge(self) -> dict[str, Any]:
        project = self.agent.projects[self.project]
        if "blender" not in project.apps:
            return {"ok": False, "summary": "Blender não está habilitado neste projeto"}
        installed = self.agent.execute("blender.adoption_install", {})
        if not installed.ok:
            return self._result(installed)
        connection = self.blender_prepare()
        return {
            "ok": True,
            "summary": installed.summary,
            "data": {
                "installation": installed.data,
                "connection": connection.get("data", {}),
            },
        }

    def blender_instances(self) -> dict[str, Any]:
        return self._result(self.agent.execute("blender.instances", {}))

    def blender_adopt(self, pid: int, allow_blank: bool = False) -> dict[str, Any]:
        try:
            selected_pid = int(pid)
        except (TypeError, ValueError):
            return {"ok": False, "summary": "PID do Blender inválido"}
        if selected_pid <= 0:
            return {"ok": False, "summary": "PID do Blender inválido"}

        adopted = self.agent.execute(
            "blender.adopt",
            {
                "project": self.project,
                "pid": selected_pid,
                "allow_blank": bool(allow_blank),
                "wait_seconds": 8.0,
            },
        )
        if not adopted.ok:
            return self._result(adopted)
        presence = adopted.data.get("presence") or {}
        return {
            "ok": True,
            "summary": adopted.summary,
            "data": {
                "state": "adopted_blank" if allow_blank else "adopted",
                "project": self.project,
                "pid": selected_pid,
                "file": presence.get("file"),
                "can_start": False,
                "can_capture": True,
                "requires_restart": False,
            },
        }

    def blender_start(self) -> dict[str, Any]:
        project = self.agent.projects[self.project]
        if "blender" not in project.apps:
            return {"ok": False, "summary": "Blender não está habilitado neste projeto"}

        started = self.agent.execute(
            "blender.live_start",
            {"project": self.project, "wait_seconds": 60.0},
        )
        if not started.ok:
            return self._result(started)

        status = self.agent.execute("blender.live_status", {"project": self.project})
        if not status.ok:
            return self._result(started)
        presence = status.data.get("presence") or {}
        return {
            "ok": True,
            "summary": started.summary,
            "data": {
                "state": "connected",
                "project": self.project,
                "pid": presence.get("pid") or started.data.get("pid"),
                "file": presence.get("file"),
                "can_start": False,
                "can_capture": True,
                "requires_restart": False,
            },
        }


def main() -> int:
    try:
        import webview
    except ImportError as error:
        raise SystemExit("pywebview is required for ORDAX Dev") from error

    config = AgentConfig.from_env()
    lock = SingleInstanceLock(config.state_dir / "studio-web.lock")
    if not lock.acquire():
        return 0
    try:
        api = StudioProductApi(ActionRegistry(config))
        html = Path(__file__).with_name("studio_product.html").resolve()
        webview.create_window(
            APP_NAME,
            url=html.as_uri(),
            js_api=api,
            width=1600,
            height=960,
            min_size=(1180, 720),
        )
        webview.start(gui="edgechromium", debug=False)
        return 0
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
