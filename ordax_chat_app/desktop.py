"""ORDAX Dev desktop shell with embedded ChatGPT-plan chat."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .auth import resolve_chat_app_state_dir
from .instance_lock import SingleInstanceLock
from .runtime import OrdaxChatRuntime


APP_NAME = "ORDAX Dev"


class DesktopApi:
    def __init__(self, runtime: OrdaxChatRuntime | None = None):
        self.runtime = runtime or OrdaxChatRuntime()

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
            }
        return self._guard(build)

    def connect_chatgpt(self) -> dict[str, Any]:
        return self._guard(
            lambda: {
                "account": self.runtime.connect_chatgpt(),
                "models": self.runtime.models(),
            }
        )

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
    try:
        api = DesktopApi()
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
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
