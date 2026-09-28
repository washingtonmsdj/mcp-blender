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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
