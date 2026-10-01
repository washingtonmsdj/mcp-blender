"""ORDAX Dev desktop shell with embedded ChatGPT-plan chat."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import webbrowser
from typing import Any, Callable

from .auth import resolve_chat_app_state_dir
from .autonomy_service import AutonomyService
from .instance_lock import SingleInstanceLock
from .runtime import OrdaxChatRuntime
from .web_bridge import WebBridgeManager


APP_NAME = "ORDAX Dev"
NORMAL_CHAT_URL = "https://chatgpt.com/"
NORMAL_CHAT_MCP_ENDPOINT = "https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp"


class DesktopApi:
    def __init__(
        self,
        runtime: OrdaxChatRuntime | None = None,
        *,
        autonomy: AutonomyService | None = None,
        web_bridge: WebBridgeManager | None = None,
        auto_resume: bool = True,
    ):
        self.runtime = runtime or OrdaxChatRuntime()
        self.autonomy = autonomy or AutonomyService(self.runtime)
        self.web_bridge = web_bridge or WebBridgeManager()
        self.autonomy_resume_error: str | None = None
        if auto_resume:
            try:
                self.autonomy.resume_persisted()
            except Exception as error:
                self.autonomy_resume_error = f"{type(error).__name__}: {error}"

    @staticmethod
    def _guard(fn: Callable[[], Any]) -> dict[str, Any]:
        try:
            return {"ok": True, "data": fn()}
        except Exception as error:
            return {
                "ok": False,
                "summary": f"{type(error).__name__}: {error}",
            }

    def bootstrap(self) -> dict[str, Any]:
        def build():
            account = self.runtime.account_status()
            projects = self.runtime.projects()
            default_project = self.runtime.agent.config.default_project
            if not any(item.get("slug") == default_project for item in projects):
                default_project = projects[0]["slug"] if projects else None
            models: list[dict[str, Any]] = []
            model_error = None
            if account["connected"]:
                try:
                    models = self.runtime.models()
                except Exception as error:
                    model_error = f"{type(error).__name__}: {error}"
            return {
                "product": APP_NAME,
                "account": account,
                "projects": projects,
                "default_project": default_project,
                "models": models,
                "model_error": model_error,
                "threads": self.runtime.threads(default_project) if default_project else [],
                "autonomy": self.autonomy.status(),
                "autonomy_resume_error": self.autonomy_resume_error,
                "chat_modes": {
                    "default": "normal",
                    "normal": {
                        "label": "Chat normal",
                        "uses_work_codex_quota": False,
                        "mcp_endpoint": NORMAL_CHAT_MCP_ENDPOINT,
                        "chat_url": NORMAL_CHAT_URL,
                        "web_bridge": self.web_bridge.status(),
                    },
                    "agent": {
                        "label": "Agent / Responses",
                        "uses_work_codex_quota": True,
                    },
                },
            }
        return self._guard(build)

    def normal_chat_info(self) -> dict[str, Any]:
        return {
            "mode": "normal",
            "chat_url": NORMAL_CHAT_URL,
            "mcp_endpoint": NORMAL_CHAT_MCP_ENDPOINT,
            "uses_work_codex_quota": False,
            "runtime": "ORDAX remote MCP",
        }

    def open_normal_chat(self) -> dict[str, Any]:
        def open_chat():
            opened = webbrowser.open(NORMAL_CHAT_URL, new=2)
            return {
                **self.normal_chat_info(),
                "opened": bool(opened),
            }
        return self._guard(open_chat)

    def web_bridge_status(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.status)

    def web_bridge_configure(self, tunnel_id: str, api_key: str) -> dict[str, Any]:
        return self._guard(
            lambda: self.web_bridge.configure(
                str(tunnel_id or ""),
                str(api_key or ""),
            )
        )

    def web_bridge_install(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.install_client)

    def web_bridge_start(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.start)

    def web_bridge_stop(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.stop)

    def web_bridge_disconnect(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.disconnect)

    def web_bridge_open_tunnels(self) -> dict[str, Any]:
        return self._guard(
            lambda: {"opened": self.web_bridge.open_tunnels_page()}
        )

    def web_bridge_open_api_keys(self) -> dict[str, Any]:
        return self._guard(
            lambda: {"opened": self.web_bridge.open_api_keys_page()}
        )

    def connect_chatgpt(self) -> dict[str, Any]:
        def connect():
            account = self.runtime.connect_chatgpt()
            resume = self.autonomy.resume_persisted()
            return {
                "account": account,
                "models": self.runtime.models(),
                "autonomy": resume,
            }
        return self._guard(connect)

    def models(self) -> dict[str, Any]:
        return self._guard(self.runtime.models)

    def threads(self, project: str) -> dict[str, Any]:
        return self._guard(lambda: self.runtime.threads(str(project or "")))

    def create_thread(self, project: str, model: str) -> dict[str, Any]:
        return self._guard(
            lambda: self.runtime.new_thread(
                project=str(project or ""),
                model=str(model or ""),
            )
        )

    def open_thread(self, thread_id: str) -> dict[str, Any]:
        return self._guard(
            lambda: {
                "thread": self.runtime.conversations.thread(str(thread_id or "")),
                "messages": self.runtime.messages(str(thread_id or "")),
            }
        )

    def send_message(self, thread_id: str, text: str) -> dict[str, Any]:
        return self._guard(
            lambda: asdict(
                self.runtime.send_message(
                    str(thread_id or ""),
                    str(text or ""),
                )
            )
        )

    def orchestrator_status(self, project: str) -> dict[str, Any]:
        return self._guard(
            lambda: self.runtime.orchestrator.status(str(project or ""))
        )

    def orchestrator_agent_create(
        self,
        project: str,
        name: str,
        role: str,
        parent_agent_id: str | None = None,
    ) -> dict[str, Any]:
        return self._guard(
            lambda: self.runtime.orchestrator.create_agent(
                str(project or ""),
                str(name or ""),
                str(role or ""),
                parent_agent_id=str(parent_agent_id or "") or None,
            )
        )

    def orchestrator_agent_state(self, agent_id: str, state: str) -> dict[str, Any]:
        return self._guard(
            lambda: self.runtime.orchestrator.set_agent_state(
                str(agent_id or ""),
                str(state or ""),
            )
        )

    def orchestrator_work_enqueue(
        self,
        project: str,
        agent_id: str,
        title: str,
        instruction: str,
        priority: int = 50,
    ) -> dict[str, Any]:
        def enqueue():
            selected = self.runtime.agent.select_available_project(str(project or ""))
            agent = self.runtime.orchestrator.get_agent(str(agent_id or ""))
            if agent["project_slug"] != selected:
                raise ValueError("agent does not belong to the selected project")
            return self.runtime.orchestrator.enqueue_work(
                agent["id"],
                str(title or ""),
                str(instruction or ""),
                priority=int(priority),
            )
        return self._guard(enqueue)

    def capability_status(self, project: str) -> dict[str, Any]:
        def status():
            selected = self.runtime.agent.select_available_project(str(project or ""))
            return self.runtime.policy.project(selected)
        return self._guard(status)

    def capability_set(self, project: str, capability: str, enabled: bool) -> dict[str, Any]:
        def update():
            selected = self.runtime.agent.select_available_project(str(project or ""))
            result = self.runtime.policy.set(selected, str(capability or ""), bool(enabled))
            return {
                "grant": result,
                "capabilities": self.runtime.policy.project(selected),
            }
        return self._guard(update)

    def autonomy_status(self) -> dict[str, Any]:
        return self._guard(self.autonomy.status)

    def autonomy_start(self, project: str, model: str) -> dict[str, Any]:
        def start():
            selected = self.runtime.agent.select_available_project(str(project or ""))
            return self.autonomy.start(
                model=str(model or ""),
                project_slugs=[selected],
            )
        return self._guard(start)

    def autonomy_stop(self) -> dict[str, Any]:
        return self._guard(self.autonomy.stop)

    def account_status(self) -> dict[str, Any]:
        return self._guard(self.runtime.account_status)


def main() -> int:
    try:
        import webview
    except ImportError as error:
        raise SystemExit("pywebview is required for ORDAX Dev") from error

    state_dir = resolve_chat_app_state_dir()
    lock = SingleInstanceLock(state_dir / "ordax-dev.lock")
    if not lock.acquire():
        return 0
    api = DesktopApi()
    try:
        html = Path(__file__).with_name("app.html").resolve()
        webview.create_window(
            APP_NAME,
            url=html.as_uri(),
            js_api=api,
            width=1560,
            height=940,
            min_size=(1120, 680),
        )
        webview.start(gui="edgechromium", debug=False)
        return 0
    finally:
        api.autonomy.stop(timeout_seconds=3.0, disable_persisted=False)
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
