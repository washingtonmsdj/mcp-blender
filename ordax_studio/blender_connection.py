from __future__ import annotations

from typing import Any

from ordax_dev_agent.actions import ActionRegistry


def prepare_blender_connection(
    agent: ActionRegistry,
    project_slug: str,
    *,
    wait_seconds: float = 4.0,
) -> dict[str, Any]:
    """Resolve one Blender project's connection state without opening a new window."""
    project = agent.projects[project_slug]
    if "blender" not in project.apps:
        return {
            "ok": True,
            "data": {
                "state": "not_blender",
                "project": project_slug,
                "can_start": False,
                "can_capture": False,
                "requires_restart": False,
            },
        }

    status = agent.execute("blender.live_status", {"project": project_slug})
    if status.ok:
        presence = status.data.get("presence") or {}
        return {
            "ok": True,
            "summary": "Blender já conectado",
            "data": {
                "state": "connected",
                "project": project_slug,
                "pid": presence.get("pid"),
                "file": presence.get("file"),
                "can_start": False,
                "can_capture": True,
                "requires_restart": False,
            },
        }

    adopted = agent.execute(
        "blender.adopt",
        {"project": project_slug, "wait_seconds": max(0.5, min(float(wait_seconds), 10.0))},
    )
    if adopted.ok:
        presence = adopted.data.get("presence") or {}
        return {
            "ok": True,
            "summary": adopted.summary,
            "data": {
                "state": "adopted",
                "project": project_slug,
                "pid": adopted.data.get("pid") or presence.get("pid"),
                "file": presence.get("file"),
                "can_start": False,
                "can_capture": True,
                "requires_restart": False,
            },
        }

    if adopted.data.get("ambiguous"):
        return {
            "ok": True,
            "summary": "Mais de uma janela Blender corresponde ao projeto",
            "data": {
                "state": "ambiguous",
                "project": project_slug,
                "instances": adopted.data.get("instances", []),
                "requires_pid": True,
                "can_start": False,
                "can_capture": False,
                "requires_restart": False,
            },
        }

    if adopted.data.get("no_match"):
        instances = agent.execute("blender.instances", {})
        if not instances.ok:
            return {"ok": False, "summary": instances.summary, "data": instances.data}
        unmanaged = instances.data.get("unmanaged_blender_pids") or []
        if unmanaged:
            return {
                "ok": True,
                "summary": "Blender aberto sem o bridge ORDAX carregado",
                "data": {
                    "state": "restart_required",
                    "project": project_slug,
                    "blender_pids": unmanaged,
                    "install_action": "blender.adoption_install",
                    "bridge_installable": True,
                    "can_start": False,
                    "can_capture": False,
                    "requires_restart": True,
                },
            }
        return {
            "ok": True,
            "summary": "Nenhuma janela Blender aberta para este projeto",
            "data": {
                "state": "idle",
                "project": project_slug,
                "can_start": True,
                "can_capture": False,
                "requires_restart": False,
            },
        }

    return {"ok": False, "summary": adopted.summary, "data": adopted.data}
