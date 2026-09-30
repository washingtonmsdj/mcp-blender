from __future__ import annotations

from typing import Any

from ordax_dev_agent.actions import ActionRegistry


def _state(
    project: str,
    state: str,
    *,
    summary: str | None = None,
    can_start: bool = False,
    can_capture: bool = False,
    requires_restart: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "state": state,
        "project": project,
        "can_start": can_start,
        "can_capture": can_capture,
        "requires_restart": requires_restart,
        **extra,
    }
    result: dict[str, Any] = {"ok": True, "data": payload}
    if summary:
        result["summary"] = summary
    return result


def prepare_blender_connection(
    agent: ActionRegistry,
    project_slug: str,
    *,
    wait_seconds: float = 4.0,
) -> dict[str, Any]:
    """Resolve one Blender project's actionable connection state.

    This is intentionally side-effect-light: it may adopt an already prepared
    Blender window, but it never launches Blender and never restarts a process.
    The returned state is suitable for both the Studio UI and MCP clients.
    """
    project = agent.projects[project_slug]
    if "blender" not in project.apps:
        return _state(project_slug, "not_blender")

    status = agent.execute("blender.live_status", {"project": project_slug})
    if status.ok:
        presence = status.data.get("presence") or {}
        return _state(
            project_slug,
            "connected",
            summary="Blender já conectado",
            can_capture=True,
            pid=presence.get("pid"),
            file=presence.get("file"),
        )

    adopted = agent.execute(
        "blender.adopt",
        {
            "project": project_slug,
            "wait_seconds": max(0.5, min(float(wait_seconds), 10.0)),
        },
    )
    if adopted.ok:
        presence = adopted.data.get("presence") or {}
        return _state(
            project_slug,
            "adopted",
            summary=adopted.summary,
            can_capture=True,
            pid=adopted.data.get("pid") or presence.get("pid"),
            file=presence.get("file"),
        )

    if adopted.data.get("restart_required"):
        pid = adopted.data.get("pid")
        pids = [int(pid)] if pid else []
        return _state(
            project_slug,
            "restart_required",
            summary=adopted.summary,
            requires_restart=True,
            blender_pids=pids,
            install_action=adopted.data.get("install_action") or "blender.adoption_install",
            bridge_installable=True,
        )

    if adopted.data.get("ambiguous"):
        return _state(
            project_slug,
            "ambiguous",
            summary="Mais de uma janela Blender corresponde ao projeto",
            instances=adopted.data.get("instances", []),
            requires_pid=True,
        )

    if not adopted.data.get("no_match"):
        return {"ok": False, "summary": adopted.summary, "data": adopted.data}

    windows = agent.execute("blender.instances", {})
    if not windows.ok:
        return {"ok": False, "summary": windows.summary, "data": windows.data}

    data = windows.data
    instances = data.get("instances") or []
    ready_pids = {int(pid) for pid in (data.get("ready_pids") or [])}
    clean_blank = [
        item
        for item in instances
        if int(item.get("pid", -1)) in ready_pids
        and not str(item.get("file") or "").strip()
        and not str(item.get("attached_project") or "").strip()
        and not bool(item.get("is_dirty"))
    ]

    if len(clean_blank) == 1:
        pid = int(clean_blank[0]["pid"])
        blank = agent.execute(
            "blender.adopt",
            {
                "project": project_slug,
                "pid": pid,
                "allow_blank": True,
                "wait_seconds": max(0.5, min(float(wait_seconds), 10.0)),
            },
        )
        if not blank.ok:
            return {"ok": False, "summary": blank.summary, "data": blank.data}
        return _state(
            project_slug,
            "adopted_blank",
            summary="Janela Blender vazia adotada pelo projeto",
            can_capture=True,
            pid=pid,
            file="",
        )

    if len(clean_blank) > 1:
        return _state(
            project_slug,
            "blank_ambiguous",
            summary="Há várias janelas Blender vazias disponíveis",
            instances=clean_blank,
            blender_pids=[int(item["pid"]) for item in clean_blank],
            requires_pid=True,
        )

    restart = [int(pid) for pid in (data.get("restart_required_pids") or [])]
    unmanaged = [int(pid) for pid in (data.get("unmanaged_blender_pids") or [])]
    if restart or unmanaged:
        return _state(
            project_slug,
            "restart_required",
            summary=(
                "Blender aberto com bridge ORDAX desatualizado"
                if restart
                else "Blender aberto sem o bridge ORDAX carregado"
            ),
            requires_restart=True,
            blender_pids=restart or unmanaged,
            install_action="blender.adoption_install",
            bridge_installable=True,
        )

    occupied = [
        item for item in instances if str(item.get("attached_project") or "").strip()
    ]
    if occupied:
        return _state(
            project_slug,
            "occupied",
            summary="As janelas Blender abertas já pertencem a outros projetos",
            instances=occupied,
        )

    return _state(
        project_slug,
        "idle",
        summary="Nenhuma janela Blender aberta para este projeto",
        can_start=True,
    )
