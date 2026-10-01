from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .product_remote_client import ProductRemoteClient


mcp = FastMCP("ordax-studio-remote")


def _access_token() -> str:
    token = os.environ.get("ORDAX_PRODUCT_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("ORDAX_PRODUCT_ACCESS_TOKEN is required")
    return token


def _base_url() -> str:
    value = os.environ.get(
        "ORDAX_PRODUCT_CONTROL_PLANE_URL",
        "https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev",
    ).strip()
    if not value:
        raise RuntimeError("ORDAX_PRODUCT_CONTROL_PLANE_URL is required")
    return value


def _invoke(
    *,
    device_id: str,
    action: str,
    project: str | None = None,
    space_id: str | None = None,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    token = _access_token()
    with ProductRemoteClient(_base_url()) as client:
        request_id = client.submit_action(
            token,
            device_id=device_id,
            action=action,
            project=project,
            space_id=space_id,
            arguments=arguments,
        )
        result = client.wait_action(token, request_id)
    return {
        "request_id": request_id,
        "status": result.get("status"),
        "result": result.get("result"),
        "error_code": result.get("error_code"),
        "created_at": result.get("created_at"),
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
    }


@mcp.tool()
def product_session() -> dict[str, Any]:
    """Return the authenticated OrdaX Product subject for this MCP host."""
    token = _access_token()
    with ProductRemoteClient(_base_url()) as client:
        return client.session(token)


@mcp.tool()
def product_targets(space_id: str | None = None) -> list[dict[str, Any]]:
    """List only devices and grants authorized for the authenticated Product subject."""
    token = _access_token()
    with ProductRemoteClient(_base_url()) as client:
        return client.targets(token, space_id=space_id)


@mcp.tool()
def projects_list(
    device_id: str,
    space_id: str | None = None,
) -> dict[str, Any]:
    """List projects visible on one authorized device."""
    return _invoke(
        device_id=device_id,
        action="projects.list",
        space_id=space_id,
        arguments={},
    )


@mcp.tool()
def repository_catalog(
    device_id: str,
    space_id: str | None = None,
) -> dict[str, Any]:
    """List canonical ORDAX Studio repositories on one authorized device."""
    return _invoke(
        device_id=device_id,
        action="workspace.repository_catalog",
        space_id=space_id,
        arguments={},
    )


@mcp.tool()
def project_inventory(
    device_id: str,
    project: str,
    max_depth: int = 4,
    max_entries: int = 500,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Inspect a bounded read-only inventory of one granted project."""
    return _invoke(
        device_id=device_id,
        action="project.inventory",
        project=project,
        space_id=space_id,
        arguments={
            "project": project,
            "max_depth": max_depth,
            "max_entries": max_entries,
        },
    )


@mcp.tool()
def project_text_read(
    device_id: str,
    project: str,
    path: str,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read one granted project-relative text file."""
    return _invoke(
        device_id=device_id,
        action="project.text_read",
        project=project,
        space_id=space_id,
        arguments={"project": project, "path": path},
    )


@mcp.tool()
def project_health(
    device_id: str,
    project: str,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read sanitized ORDAX Studio health for one granted project."""
    return _invoke(
        device_id=device_id,
        action="agent.project_health",
        project=project,
        space_id=space_id,
        arguments={"project": project},
    )


@mcp.tool()
def project_search(
    device_id: str,
    project: str,
    query: str,
    max_results: int = 40,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Search bounded approved text sources in one granted project."""
    return _invoke(
        device_id=device_id,
        action="project.search_text",
        project=project,
        space_id=space_id,
        arguments={"project": project, "query": query, "max_results": max_results},
    )


@mcp.tool()
def project_read_batch(
    device_id: str,
    project: str,
    paths: list[str],
    max_total_bytes: int = 393216,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read several approved text files from one granted project."""
    return _invoke(
        device_id=device_id,
        action="project.text_read_batch",
        project=project,
        space_id=space_id,
        arguments={"project": project, "paths": paths, "max_total_bytes": max_total_bytes},
    )


@mcp.tool()
def project_preview_status(
    device_id: str,
    project: str,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read sanitized project preview/runtime state without exposing local process details."""
    return _invoke(
        device_id=device_id,
        action="project.preview_status",
        project=project,
        space_id=space_id,
        arguments={"project": project},
    )


@mcp.tool()
def git_status(
    device_id: str,
    project: str,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read Git status for one granted project."""
    return _invoke(
        device_id=device_id,
        action="git.status",
        project=project,
        space_id=space_id,
        arguments={"project": project},
    )


@mcp.tool()
def git_diff(
    device_id: str,
    project: str,
    paths: list[str] | None = None,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read a bounded Git diff for one granted project."""
    arguments: dict[str, Any] = {"project": project}
    if paths is not None:
        arguments["paths"] = paths
    return _invoke(
        device_id=device_id,
        action="git.diff",
        project=project,
        space_id=space_id,
        arguments=arguments,
    )


@mcp.tool()
def artifacts_list(
    device_id: str,
    project: str,
    max_items: int = 100,
    space_id: str | None = None,
) -> dict[str, Any]:
    """List bounded metadata for artifacts in one granted project."""
    return _invoke(
        device_id=device_id,
        action="artifacts.list",
        project=project,
        space_id=space_id,
        arguments={"project": project, "max_items": max_items},
    )


@mcp.tool()
def artifact_preview(
    device_id: str,
    project: str,
    artifact_name: str | None = None,
    project_artifact_path: str | None = None,
    thumbnail: bool = False,
    max_bytes: int = 262144,
    max_width: int = 480,
    max_height: int = 320,
    quality: int = 72,
    space_id: str | None = None,
) -> dict[str, Any]:
    """Read a bounded preview of one granted artifact."""
    arguments: dict[str, Any] = {
        "project": project,
        "thumbnail": thumbnail,
        "max_bytes": max_bytes,
        "max_width": max_width,
        "max_height": max_height,
        "quality": quality,
    }
    if artifact_name is not None:
        arguments["artifact_name"] = artifact_name
    if project_artifact_path is not None:
        arguments["project_artifact_path"] = project_artifact_path
    return _invoke(
        device_id=device_id,
        action="artifact.preview",
        project=project,
        space_id=space_id,
        arguments=arguments,
    )


@mcp.tool()
def project_text_write(device_id: str, project: str, path: str, content: str, expected_sha256: str | None = None, create: bool = False, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "path": path, "content": content, "create": create}
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _invoke(device_id=device_id, action="project.text_write", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def project_text_patch(device_id: str, project: str, path: str, expected_sha256: str, replacements: list[dict[str, Any]], space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="project.text_patch", project=project, space_id=space_id, arguments={"project": project, "path": path, "expected_sha256": expected_sha256, "replacements": replacements})


@mcp.tool()
def workspace_file_stat(device_id: str, project: str, path: str = ".", space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="workspace.file_stat", project=project, space_id=space_id, arguments={"project": project, "path": path})


@mcp.tool()
def workspace_directory_list(device_id: str, project: str, path: str = ".", max_depth: int = 2, max_entries: int = 500, include_hidden: bool = False, space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="workspace.directory_list", project=project, space_id=space_id, arguments={"project": project, "path": path, "max_depth": max_depth, "max_entries": max_entries, "include_hidden": include_hidden})


@mcp.tool()
def workspace_text_read(device_id: str, project: str, path: str, start_line: int = 1, end_line: int | None = None, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "path": path, "start_line": start_line}
    if end_line is not None:
        arguments["end_line"] = end_line
    return _invoke(device_id=device_id, action="workspace.text_read", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def workspace_text_write(device_id: str, project: str, path: str, content: str, expected_sha256: str | None = None, create: bool = False, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "path": path, "content": content, "create": create}
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _invoke(device_id=device_id, action="workspace.text_write", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def workspace_text_patch(device_id: str, project: str, path: str, expected_sha256: str, replacements: list[dict[str, Any]], space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="workspace.text_patch", project=project, space_id=space_id, arguments={"project": project, "path": path, "expected_sha256": expected_sha256, "replacements": replacements})


@mcp.tool()
def workspace_directory_create(device_id: str, project: str, path: str, parents: bool = True, space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="workspace.directory_create", project=project, space_id=space_id, arguments={"project": project, "path": path, "parents": parents})


@mcp.tool()
def workspace_path_remove(device_id: str, project: str, path: str, expected_sha256: str | None = None, recursive: bool = False, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "path": path, "recursive": recursive}
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _invoke(device_id=device_id, action="workspace.path_remove", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def workspace_path_move(device_id: str, project: str, source: str, destination: str, expected_sha256: str | None = None, overwrite: bool = False, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "source": source, "destination": destination, "overwrite": overwrite}
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _invoke(device_id=device_id, action="workspace.path_move", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def git_command(device_id: str, project: str, args: list[str], timeout_seconds: int = 300, space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="git.command", project=project, space_id=space_id, arguments={"project": project, "args": args, "timeout_seconds": timeout_seconds})


@mcp.tool()
def terminal_exec(
    device_id: str,
    project: str,
    argv: list[str] | None = None,
    command: str | None = None,
    shell: bool = False,
    cwd: str = ".",
    timeout_seconds: int = 900,
    env: dict[str, str] | None = None,
    space_id: str | None = None,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "project": project,
        "cwd": cwd,
        "shell": shell,
        "timeout_seconds": timeout_seconds,
    }
    if argv is not None:
        arguments["argv"] = argv
    if command is not None:
        arguments["command"] = command
    if env is not None:
        arguments["env"] = env
    return _invoke(device_id=device_id, action="terminal.exec", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_status(device_id: str, project: str, space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="blender.live_status", project=project, space_id=space_id, arguments={"project": project})


@mcp.tool()
def blender_scene_snapshot(device_id: str, project: str, max_objects: int = 200, object_names: list[str] | None = None, timeout_seconds: float = 45.0, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "max_objects": max_objects, "timeout_seconds": timeout_seconds}
    if object_names is not None:
        arguments["object_names"] = object_names
    return _invoke(device_id=device_id, action="blender.live_scene_snapshot", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_object_inspect(device_id: str, project: str, object_name: str | None = None, ordax_object_id: str | None = None, timeout_seconds: float = 30.0, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "timeout_seconds": timeout_seconds}
    if object_name is not None:
        arguments["object_name"] = object_name
    if ordax_object_id is not None:
        arguments["ordax_object_id"] = ordax_object_id
    return _invoke(device_id=device_id, action="blender.live_object_inspect", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_modeling_schema(device_id: str, project: str, space_id: str | None = None) -> dict[str, Any]:
    return _invoke(device_id=device_id, action="blender.live_modeling_schema", project=project, space_id=space_id, arguments={"project": project})


@mcp.tool()
def blender_start(device_id: str, project: str, wait_seconds: float = 60.0, pid: int | None = None, adopt_blank: bool = False, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "wait_seconds": wait_seconds, "adopt_blank": adopt_blank}
    if pid is not None:
        arguments["pid"] = pid
    return _invoke(device_id=device_id, action="blender.live_start", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_transform(device_id: str, project: str, object_name: str | None = None, ordax_object_id: str | None = None, location: list[float] | None = None, rotation_euler: list[float] | None = None, scale: list[float] | None = None, dimensions: list[float] | None = None, timeout_seconds: float = 30.0, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "timeout_seconds": timeout_seconds}
    values = {"object_name": object_name, "ordax_object_id": ordax_object_id, "location": location, "rotation_euler": rotation_euler, "scale": scale, "dimensions": dimensions}
    arguments.update({key: value for key, value in values.items() if value is not None})
    return _invoke(device_id=device_id, action="blender.live_object_transform", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_create_primitive(device_id: str, project: str, name: str, primitive: str, location: list[float] | None = None, size: float | None = None, radius: float | None = None, depth: float | None = None, segments: int | None = None, timeout_seconds: float = 30.0, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "name": name, "primitive": primitive, "timeout_seconds": timeout_seconds}
    values = {"location": location, "size": size, "radius": radius, "depth": depth, "segments": segments}
    arguments.update({key: value for key, value in values.items() if value is not None})
    return _invoke(device_id=device_id, action="blender.live_create_primitive", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_apply_material(device_id: str, project: str, material_name: str, object_name: str | None = None, ordax_object_id: str | None = None, base_color: list[float] | None = None, roughness: float = 0.4, metallic: float = 0.0, transmission: float = 0.0, alpha: float = 1.0, ior: float = 1.45, surface_render_method: str | None = None, transparency_overlap: bool = True, timeout_seconds: float = 30.0, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "material_name": material_name, "roughness": roughness, "metallic": metallic, "transmission": transmission, "alpha": alpha, "ior": ior, "transparency_overlap": transparency_overlap, "timeout_seconds": timeout_seconds}
    values = {"object_name": object_name, "ordax_object_id": ordax_object_id, "base_color": base_color, "surface_render_method": surface_render_method}
    arguments.update({key: value for key, value in values.items() if value is not None})
    return _invoke(device_id=device_id, action="blender.live_material_apply", project=project, space_id=space_id, arguments=arguments)


@mcp.tool()
def blender_save(device_id: str, project: str, target_path: str | None = None, timeout_seconds: float = 120.0, space_id: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"project": project, "timeout_seconds": timeout_seconds}
    if target_path is not None:
        arguments["target_path"] = target_path
    return _invoke(device_id=device_id, action="blender.live_save", project=project, space_id=space_id, arguments=arguments)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
