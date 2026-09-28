from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig

from .instance_lock import SingleInstanceLock

APP_NAME = "ORDAX Studio"


class StudioApi:
    def __init__(self, agent: ActionRegistry | None = None):
        self.agent = agent or ActionRegistry(AgentConfig.from_env())
        self.store = self.agent._memory_store_instance()
        self.project = self.agent.select_available_project()
        self.session_id: int | None = None
        self._activate(self.project)

    @staticmethod
    def _result(result) -> dict[str, Any]:
        return {"ok": result.ok, "summary": result.summary, "data": result.data}

    def _project_card(self, project) -> dict[str, Any]:
        card = project.public()
        if not project.root.is_dir():
            card["repository"] = {"is_repository": False, "available": False}
            return card
        repository = self.agent.execute("git.repository_info", {"project": project.slug})
        card["repository"] = repository.data if repository.ok else {
            "is_repository": False, "error": repository.summary,
        }
        return card

    def projects_catalog(self) -> dict[str, Any]:
        result = self.agent.execute("workspace.repository_catalog", {})
        if not result.ok:
            return {"ok": False, "summary": result.summary, "projects": []}
        return {"ok": True, **result.data}

    def _activate(self, slug: str) -> None:
        project = self.agent._project({"project": slug})
        self.project = slug
        self.store.set_active_project(slug, project.root)
        resumed = self.agent.execute("session.resume", {"project": slug})
        if resumed.ok:
            self.session_id = int(resumed.data["session_id"])

    def bootstrap(self) -> dict[str, Any]:
        project = self.agent.projects[self.project]
        context = self.store.context(project.slug, project.root)
        preview = self.agent.execute("project.preview_status", {"project": self.project})
        health = self.agent.execute("agent.project_health", {"project": self.project})
        return {
            "product": APP_NAME,
            "project": self._project_card(project),
            "projects": [self._project_card(item) for item in self.agent.projects.values()],
            "session_id": self.session_id,
            "memory": {
                "memories": context.get("memories", []),
                "tasks": context.get("tasks", []),
                "checkpoints": context.get("checkpoints", []),
            },
            "preview": self._result(preview),
            "health": self._result(health),
        }

    def select_project(self, slug: str) -> dict[str, Any]:
        try:
            selected = self.agent.select_available_project(slug)
            self._activate(selected)
            return {"ok": True, "data": self.bootstrap()}
        except Exception as error:
            return {"ok": False, "summary": f"{type(error).__name__}: {error}"}

    def inventory(self) -> dict[str, Any]:
        return self._result(self.agent.execute("project.inventory", {
            "project": self.project, "max_depth": 5, "max_entries": 900,
        }))

    def read_file(self, path: str) -> dict[str, Any]:
        return self._result(self.agent.execute("project.text_read", {
            "project": self.project, "path": path,
        }))

    def save_file(self, path: str, content: str, expected_sha256: str) -> dict[str, Any]:
        return self._result(self.agent.execute("project.text_write", {
            "project": self.project, "path": path, "content": content,
            "expected_sha256": expected_sha256,
        }))

    def preview_status(self) -> dict[str, Any]:
        return self._result(self.agent.execute("project.preview_status", {"project": self.project}))

    def preview_start(self) -> dict[str, Any]:
        return self._result(self.agent.execute("project.preview_start", {"project": self.project}))

    def preview_stop(self) -> dict[str, Any]:
        return self._result(self.agent.execute("project.preview_stop", {"project": self.project}))

    def preview_capture(self) -> dict[str, Any]:
        captured = self.agent.execute("project.preview_capture", {"project": self.project})
        return self._result(captured)

    def preview_logs(self, max_bytes: int = 32768) -> dict[str, Any]:
        return self._result(self.agent.execute("project.preview_logs", {
            "project": self.project, "max_bytes": max_bytes,
        }))

    def preview_image(self) -> dict[str, Any]:
        status = self.agent.execute("project.preview_status", {"project": self.project})
        if not status.ok or not status.data.get("latest_image"):
            return {"ok": False, "summary": "Nenhuma imagem de preview disponível"}
        image = status.data["latest_image"]
        result = self.agent.execute("artifact.preview", {
            "project": self.project,
            **image["artifact_preview_payload"],
            "thumbnail": True,
            "max_width": 1600,
            "max_height": 1200,
        })
        if not result.ok:
            return self._result(result)
        return {
            "ok": True,
            "data": {
                "src": f"data:{result.data['mime_type']};base64,{result.data['base64']}",
                "artifact": image.get("path"),
                "revision": image.get("modified_at_ns"),
            },
        }

    def checkpoint(self, summary: str) -> dict[str, Any]:
        return self._result(self.agent.execute("memory.checkpoint", {
            "project": self.project, "summary": summary,
        }))

    def health(self) -> dict[str, Any]:
        return self._result(self.agent.execute("agent.project_health", {"project": self.project}))


def main() -> int:
    try:
        import webview
    except ImportError as error:
        raise SystemExit("pywebview is required for ORDAX Studio WebView shell") from error
    config = AgentConfig.from_env()
    lock = SingleInstanceLock(config.state_dir / "studio-web.lock")
    if not lock.acquire():
        return 0
    try:
        api = StudioApi(ActionRegistry(config))
        html = Path(__file__).with_name("studio.html").read_text(encoding="utf-8")
        webview.create_window(
            APP_NAME,
            html=html,
            js_api=api,
            width=1500,
            height=900,
            min_size=(1100, 700),
        )
        webview.start(gui="edgechromium", debug=False)
        return 0
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
