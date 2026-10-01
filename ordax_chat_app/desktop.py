"""ORDAX Dev desktop shell with embedded ChatGPT-plan chat."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import os
import subprocess
import webbrowser
from typing import Any, Callable

from .auth import resolve_chat_app_state_dir
from .autonomy_service import AutonomyService
from .instance_lock import SingleInstanceLock
from .runtime import OrdaxChatRuntime
from .web_bridge import WebBridgeManager
from .browser_companion import BrowserCompanionServer
from .managed_chat_browser import ManagedChatBrowser


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
        browser_companion: BrowserCompanionServer | None = None,
        managed_chat_browser: ManagedChatBrowser | None = None,
        auto_resume: bool = True,
    ):
        self.runtime = runtime or OrdaxChatRuntime()
        self.autonomy = autonomy or AutonomyService(self.runtime)
        self.web_bridge = web_bridge or WebBridgeManager()
        self.browser_companion = browser_companion or BrowserCompanionServer()
        self.managed_chat_browser = managed_chat_browser or ManagedChatBrowser(
            extension_dir=self._browser_companion_extension_dir()
        )
        self.browser_companion_start_error: str | None = None
        try:
            self.browser_companion.start()
        except OSError as error:
            self.browser_companion_start_error = f"{type(error).__name__}: {error}"
        self.autonomy_resume_error: str | None = None
        if auto_resume:
            try:
                self.autonomy.resume_persisted()
            except Exception as error:
                self.autonomy_resume_error = f"{type(error).__name__}: {error}"

    def _ensure_browser_companion(self) -> dict[str, Any]:
        status = self.browser_companion.status()
        if status.get("running"):
            self.browser_companion_start_error = None
            return status
        try:
            status = self.browser_companion.start()
            self.browser_companion_start_error = None
            return status
        except OSError as error:
            self.browser_companion_start_error = f"{type(error).__name__}: {error}"
            return {
                **self.browser_companion.status(),
                "start_error": self.browser_companion_start_error,
            }

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
                        "browser_companion": self._ensure_browser_companion(),
                        "managed_browser": self.managed_chat_browser.status(),
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

    def handoff_create(
        self,
        project: str,
        summary: str,
        next_action: str = "",
        ttl_hours: int = 24,
    ) -> dict[str, Any]:
        def create():
            selected = self.runtime.agent.select_available_project(str(project or ""))
            result = self.runtime.agent.execute(
                "handoff.create",
                {
                    "project": selected,
                    "summary": str(summary or ""),
                    "next_action": str(next_action or ""),
                    "ttl_hours": int(ttl_hours),
                },
            )
            if not result.ok:
                raise RuntimeError(result.summary)
            return result.data
        return self._guard(create)

    def handoff_get(self, project: str, handoff_id: str) -> dict[str, Any]:
        def load():
            selected = self.runtime.agent.select_available_project(str(project or ""))
            result = self.runtime.agent.execute(
                "handoff.get",
                {"project": selected, "handoff_id": str(handoff_id or "")},
            )
            if not result.ok:
                raise RuntimeError(result.summary)
            return result.data
        return self._guard(load)

    def web_bridge_startup_status(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.startup_status)

    def web_bridge_install_startup(self) -> dict[str, Any]:
        return self._guard(lambda: self.web_bridge.install_startup(start_now=True))

    def web_bridge_uninstall_startup(self) -> dict[str, Any]:
        return self._guard(self.web_bridge.uninstall_startup)

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

    def browser_companion_status(self) -> dict[str, Any]:
        return self._guard(self._ensure_browser_companion)

    def browser_companion_pair(self) -> dict[str, Any]:
        def pair():
            status = self._ensure_browser_companion()
            if not status.get("running"):
                raise RuntimeError(status.get("start_error") or "Browser Companion is unavailable")
            return self.browser_companion.new_pairing_code()
        return self._guard(pair)

    def browser_companion_conversations(self) -> dict[str, Any]:
        def conversations():
            self._ensure_browser_companion()
            return self.browser_companion.conversations()
        return self._guard(conversations)

    def browser_companion_messages(self, conversation_id: str) -> dict[str, Any]:
        def messages():
            self._ensure_browser_companion()
            return self.browser_companion.messages(str(conversation_id or ""))
        return self._guard(messages)

    def browser_companion_commands(
        self,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        return self._guard(
            lambda: self.browser_companion.commands(
                str(conversation_id or "") or None,
                limit=int(limit),
            )
        )

    def browser_companion_new_chat(self, text: str) -> dict[str, Any]:
        def create():
            status = self._ensure_browser_companion()
            if not status.get("running"):
                raise RuntimeError(status.get("start_error") or "Browser Companion is unavailable")
            if int(status.get("paired_clients") or 0) < 1:
                raise RuntimeError(
                    "Browser Companion is not paired yet; open the dedicated ChatGPT browser first"
                )
            command = self.browser_companion.new_chat(str(text or ""))
            browser = self.managed_chat_browser.status()
            if not browser.get("running"):
                browser = self.managed_chat_browser.start()
            return {
                "command": command,
                "opened": bool(browser.get("running")),
                "chat_url": NORMAL_CHAT_URL,
                "managed_browser": browser,
            }
        return self._guard(create)

    def browser_companion_send(self, conversation_id: str, text: str) -> dict[str, Any]:
        def send():
            status = self._ensure_browser_companion()
            if not status.get("running"):
                raise RuntimeError(status.get("start_error") or "Browser Companion is unavailable")
            return self.browser_companion.send(
                str(conversation_id or ""),
                str(text or ""),
            )
        return self._guard(send)

    @staticmethod
    def _browser_companion_extension_dir() -> Path:
        packaged = os.environ.get("ORDAX_PACKAGED_ROOT")
        root = Path(packaged).expanduser().resolve() if packaged else Path(__file__).resolve().parents[1]
        return (root / "browser_extension").resolve()

    def managed_chat_browser_status(self) -> dict[str, Any]:
        return self._guard(self.managed_chat_browser.status)

    def managed_chat_browser_start(self) -> dict[str, Any]:
        def start():
            companion = self._ensure_browser_companion()
            if not companion.get("running"):
                raise RuntimeError(
                    companion.get("start_error") or "Browser Companion is unavailable"
                )
            pairing = self.browser_companion.new_pairing_code()
            bootstrap_url = "http://127.0.0.1:%d/bootstrap?code=%s" % (
                int(pairing["port"]),
                str(pairing["code"]),
            )
            browser = self.managed_chat_browser.start(initial_url=bootstrap_url)
            return {
                **browser,
                "auto_pair": True,
                "pairing_expires_at": pairing["expires_at"],
            }
        return self._guard(start)

    def managed_chat_browser_stop(self) -> dict[str, Any]:
        return self._guard(self.managed_chat_browser.stop)

    def browser_companion_extension_path(self) -> dict[str, Any]:
        path = self._browser_companion_extension_dir()
        if not path.is_dir():
            raise RuntimeError(f"Browser Companion extension is missing: {path}")
        return {"path": str(path)}

    def browser_companion_open_extension_folder(self) -> dict[str, Any]:
        data = self.browser_companion_extension_path()
        path = str(data["path"])
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", path], shell=False)
        else:
            webbrowser.open(Path(path).as_uri(), new=2)
        return data

    def browser_companion_open_extensions_page(self) -> dict[str, Any]:
        status = self.managed_chat_browser.status()
        browser = status.get("browser")
        if not browser:
            raise RuntimeError("Chrome or Edge was not found")
        name = Path(str(browser)).name.lower()
        url = "edge://extensions/" if "edge" in name else "chrome://extensions/"
        subprocess.Popen([str(browser), url], shell=False)
        return {"browser": str(browser), "url": url}

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


def run_desktop(api_factory=DesktopApi) -> int:
    try:
        import webview
    except ImportError as error:
        raise SystemExit("pywebview is required for ORDAX Dev") from error

    state_dir = resolve_chat_app_state_dir()
    lock = SingleInstanceLock(state_dir / "ordax-dev.lock")
    if not lock.acquire():
        return 0
    api = api_factory()
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
        try:
            api.browser_companion.close()
        except Exception:
            pass
        lock.release()


def main() -> int:
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
