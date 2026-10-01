from __future__ import annotations

from pathlib import Path
from typing import Any

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig

from .blender_connection import prepare_blender_connection
from .instance_lock import SingleInstanceLock
from .product_auth import ProductAccountError, connect_existing_device
from .web_desktop import APP_NAME, StudioApi


class StudioProductApi(StudioApi):
    """Windows product surface layered over the canonical Studio API.

    The base Studio API remains provider-neutral. Account authentication,
    device ownership and interactive desktop lifecycle operations live here so
    development hosts do not need to own or store Product credentials.
    """

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
