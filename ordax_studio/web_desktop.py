from __future__ import annotations

import json
import os
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
        card["preview_mode"] = self.agent._preview_mode(project)
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
        startup = self.startup_project()
        return {
            "ok": True,
            **result.data,
            "startup_project": startup.get("project") if startup.get("ok") else None,
        }

    def startup_project(self) -> dict[str, Any]:
        requested = str(os.environ.get("ORDAX_STUDIO_OPEN_PROJECT") or "").strip()
        if not requested:
            return {"ok": True, "project": None}
        try:
            selected = self.agent.select_available_project(requested)
        except Exception as error:
            return {"ok": False, "summary": f"{type(error).__name__}: {error}", "project": None}
        return {"ok": True, "project": selected}

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
        modeling = (
            self.agent.execute("blender.live_modeling_schema", {"project": self.project})
            if "blender" in project.apps
            else None
        )
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
            "modeling": self._result(modeling) if modeling is not None else {"ok": True, "data": None},
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

    def blender_prepare(self) -> dict[str, Any]:
        project = self.agent.projects[self.project]
        if "blender" not in project.apps:
            return {"ok": True, "data": {"state": "not_blender", "project": self.project}}

        status = self.agent.execute("blender.live_status", {"project": self.project})
        if status.ok:
            presence = status.data.get("presence") or {}
            return {
                "ok": True,
                "summary": "Blender já conectado",
                "data": {
                    "state": "connected",
                    "project": self.project,
                    "pid": presence.get("pid"),
                    "file": presence.get("file"),
                },
            }

        adopted = self.agent.execute(
            "blender.adopt",
            {"project": self.project, "wait_seconds": 4.0},
        )
        if adopted.ok:
            return {
                "ok": True,
                "summary": adopted.summary,
                "data": {
                    "state": "adopted",
                    "project": self.project,
                    "pid": adopted.data.get("pid"),
                    "file": (adopted.data.get("presence") or {}).get("file"),
                },
            }
        if adopted.data.get("restart_required"):
            return {
                "ok": True,
                "summary": adopted.summary,
                "data": {
                    "state": "restart_required",
                    "project": self.project,
                    "blender_pids": [adopted.data.get("pid")],
                    "install_action": adopted.data.get("install_action"),
                },
            }
        if adopted.data.get("ambiguous"):
            return {
                "ok": True,
                "summary": "Mais de uma janela Blender corresponde ao projeto",
                "data": {
                    "state": "ambiguous",
                    "project": self.project,
                    "instances": adopted.data.get("instances", []),
                },
            }
        if adopted.data.get("no_match"):
            windows = self.agent.execute("blender.instances", {})
            if windows.ok:
                data = windows.data
                instances = data.get("instances") or []
                ready_pids = set(data.get("ready_pids") or [])
                clean_blank = [
                    item for item in instances
                    if int(item.get("pid", -1)) in ready_pids
                    and not str(item.get("file") or "").strip()
                    and not str(item.get("attached_project") or "").strip()
                    and not bool(item.get("is_dirty"))
                ]
                if len(clean_blank) == 1:
                    pid = int(clean_blank[0]["pid"])
                    blank = self.agent.execute(
                        "blender.adopt",
                        {
                            "project": self.project,
                            "pid": pid,
                            "allow_blank": True,
                            "wait_seconds": 4.0,
                        },
                    )
                    if blank.ok:
                        return {
                            "ok": True,
                            "summary": "Janela Blender vazia adotada pelo projeto",
                            "data": {
                                "state": "adopted_blank",
                                "project": self.project,
                                "pid": pid,
                                "file": "",
                            },
                        }
                    return self._result(blank)
                if len(clean_blank) > 1:
                    return {
                        "ok": True,
                        "summary": "Há várias janelas Blender vazias disponíveis",
                        "data": {
                            "state": "blank_ambiguous",
                            "project": self.project,
                            "blender_pids": [int(item["pid"]) for item in clean_blank],
                        },
                    }
                restart = data.get("restart_required_pids") or []
                if restart:
                    return {
                        "ok": True,
                        "summary": "Blender aberto com bridge ORDAX desatualizado",
                        "data": {
                            "state": "restart_required",
                            "project": self.project,
                            "blender_pids": restart,
                            "install_action": "blender.adoption_install",
                        },
                    }
                unmanaged = data.get("unmanaged_blender_pids") or []
                if unmanaged:
                    return {
                        "ok": True,
                        "summary": "Blender aberto sem o bridge ORDAX carregado",
                        "data": {
                            "state": "restart_required",
                            "project": self.project,
                            "blender_pids": unmanaged,
                            "install_action": "blender.adoption_install",
                        },
                    }
                occupied = [
                    item for item in instances
                    if str(item.get("attached_project") or "").strip()
                ]
                if occupied:
                    return {
                        "ok": True,
                        "summary": "As janelas Blender abertas já pertencem a outros projetos",
                        "data": {
                            "state": "occupied",
                            "project": self.project,
                            "instances": occupied,
                        },
                    }
            return {
                "ok": True,
                "summary": "Nenhuma janela Blender aberta para este projeto",
                "data": {"state": "idle", "project": self.project},
            }
        return self._result(adopted)

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

    def task_add(self, title: str) -> dict[str, Any]:
        title = str(title or "").strip()
        if not title:
            return {"ok": False, "summary": "A tarefa não pode ficar vazia"}
        return self._result(self.agent.execute("memory.task_add", {
            "project": self.project, "title": title,
        }))

    def checkpoint(self, summary: str) -> dict[str, Any]:
        return self._result(self.agent.execute("memory.checkpoint", {
            "project": self.project, "summary": summary,
        }))

    def health(self) -> dict[str, Any]:
        return self._result(self.agent.execute("agent.project_health", {"project": self.project}))

    def briefing(self) -> dict[str, Any]:
        return self._result(self.agent.execute("agent.project_briefing", {"project": self.project}))

    def search(self, query: str, max_results: int = 50) -> dict[str, Any]:
        return self._result(self.agent.execute("project.search_text", {
            "project": self.project, "query": query, "max_results": max_results,
        }))

    def git_diff(self) -> dict[str, Any]:
        return self._result(self.agent.execute("git.diff", {"project": self.project}))

    def memory_context(self) -> dict[str, Any]:
        return self._result(self.agent.execute("memory.context", {"project": self.project}))


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
        html = Path(__file__).with_name("studio.html").resolve()
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
