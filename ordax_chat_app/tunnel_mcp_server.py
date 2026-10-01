"""Restricted local MCP surface used only by ORDAX Web Bridge.

Unlike the historical developer stdio server, this surface intentionally exposes
no generic action executor. Every remote ChatGPT tool maps to one explicit,
project-scoped ORDAX action.
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


mcp = FastMCP("ordax-web-bridge")
_registry: ActionRegistry | None = None


def registry() -> ActionRegistry:
    global _registry
    if _registry is None:
        _registry = ActionRegistry(AgentConfig.from_env())
    return _registry


def _project(value: str | None) -> str:
    return registry().select_available_project(value)


def _call(action: str, project: str | None, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    selected = _project(project)
    payload = dict(arguments or {})
    payload["project"] = selected
    result = registry().execute(action, payload)
    return {"ok": result.ok, "summary": result.summary, "data": result.data}


@mcp.tool()
def projects_list() -> dict[str, Any]:
    """List registered ORDAX projects available on this computer."""
    result = registry().execute("projects.list", {})
    return {"ok": result.ok, "summary": result.summary, "data": result.data}


@mcp.tool()
def handoff_get(project: str, handoff_id: str) -> dict[str, Any]:
    """Load an expiring continuation handoff created for this project."""
    return _call("handoff.get", project, {"handoff_id": handoff_id})


@mcp.tool()
def handoff_create(
    project: str,
    summary: str,
    next_action: str = "",
    completed: list[str] | None = None,
    blockers: list[str] | None = None,
    changed_paths: list[str] | None = None,
    ttl_hours: int = 24,
) -> dict[str, Any]:
    """Create a short-lived handoff so a fresh ChatGPT conversation can continue."""
    return _call(
        "handoff.create",
        project,
        {
            "summary": summary,
            "next_action": next_action,
            "completed": list(completed or []),
            "blockers": list(blockers or []),
            "changed_paths": list(changed_paths or []),
            "ttl_hours": ttl_hours,
        },
    )


@mcp.tool()
def project_health(project: str) -> dict[str, Any]:
    """Inspect project, Git, memory and adapter health."""
    return _call("agent.project_health", project)


@mcp.tool()
def project_search(
    project: str,
    query: str,
    max_results: int = 40,
    max_files: int = 2000,
    case_sensitive: bool = False,
) -> dict[str, Any]:
    """Search text across one registered project."""
    return _call(
        "project.search_text",
        project,
        {
            "query": query,
            "max_results": max_results,
            "max_files": max_files,
            "case_sensitive": case_sensitive,
        },
    )


@mcp.tool()
def project_read_batch(
    project: str,
    paths: list[str],
    max_total_bytes: int = 393216,
) -> dict[str, Any]:
    """Read a bounded set of UTF-8 project files."""
    return _call(
        "project.text_read_batch",
        project,
        {"paths": paths, "max_total_bytes": max_total_bytes},
    )


@mcp.tool()
def workspace_file_stat(project: str, path: str = ".") -> dict[str, Any]:
    """Inspect one path inside the selected project."""
    return _call("workspace.file_stat", project, {"path": path})


@mcp.tool()
def workspace_directory_list(
    project: str,
    path: str = ".",
    max_depth: int = 2,
    max_entries: int = 500,
    include_hidden: bool = False,
) -> dict[str, Any]:
    """List project directories and files."""
    return _call(
        "workspace.directory_list",
        project,
        {
            "path": path,
            "max_depth": max_depth,
            "max_entries": max_entries,
            "include_hidden": include_hidden,
        },
    )


@mcp.tool()
def workspace_text_read(
    project: str,
    path: str,
    start_line: int = 1,
    end_line: int | None = None,
) -> dict[str, Any]:
    """Read UTF-8 text from a project-relative path."""
    arguments: dict[str, Any] = {"path": path, "start_line": start_line}
    if end_line is not None:
        arguments["end_line"] = end_line
    return _call("workspace.text_read", project, arguments)


@mcp.tool()
def workspace_text_write(
    project: str,
    path: str,
    content: str,
    expected_sha256: str | None = None,
    create: bool = False,
) -> dict[str, Any]:
    """Create or replace project text with optimistic-concurrency protection."""
    arguments: dict[str, Any] = {"path": path, "content": content, "create": create}
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _call("workspace.text_write", project, arguments)


@mcp.tool()
def workspace_text_patch(
    project: str,
    path: str,
    expected_sha256: str,
    replacements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Patch project text using exact replacements and a SHA-256 precondition."""
    return _call(
        "workspace.text_patch",
        project,
        {
            "path": path,
            "expected_sha256": expected_sha256,
            "replacements": replacements,
        },
    )


@mcp.tool()
def workspace_directory_create(
    project: str,
    path: str,
    parents: bool = True,
) -> dict[str, Any]:
    """Create a directory inside the project."""
    return _call("workspace.directory_create", project, {"path": path, "parents": parents})


@mcp.tool()
def workspace_path_move(
    project: str,
    source: str,
    destination: str,
    expected_sha256: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Move or rename one project path."""
    arguments: dict[str, Any] = {
        "source": source,
        "destination": destination,
        "overwrite": overwrite,
    }
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _call("workspace.path_move", project, arguments)


@mcp.tool()
def workspace_path_remove(
    project: str,
    path: str,
    expected_sha256: str | None = None,
    recursive: bool = False,
) -> dict[str, Any]:
    """Remove a project path. Recursive directory removal must be explicit."""
    arguments: dict[str, Any] = {"path": path, "recursive": recursive}
    if expected_sha256 is not None:
        arguments["expected_sha256"] = expected_sha256
    return _call("workspace.path_remove", project, arguments)


@mcp.tool()
def git_status(project: str) -> dict[str, Any]:
    """Read Git status for the selected project."""
    return _call("git.status", project)


@mcp.tool()
def git_diff(project: str, paths: list[str] | None = None) -> dict[str, Any]:
    """Read a bounded Git diff for the selected project."""
    return _call("git.diff", project, {"paths": list(paths or [])})


@mcp.tool()
def git_command(
    project: str,
    args: list[str],
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run one Git command in the selected repository."""
    return _call("git.command", project, {"args": args, "timeout_seconds": timeout_seconds})


@mcp.tool()
def terminal_exec(
    project: str,
    argv: list[str] | None = None,
    command: str | None = None,
    shell: bool = False,
    cwd: str = ".",
    timeout_seconds: int = 900,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute one foreground command as the local OS user for this project."""
    arguments: dict[str, Any] = {
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
    return _call("terminal.exec", project, arguments)


@mcp.tool()
def project_preview_status(project: str) -> dict[str, Any]:
    """Inspect the project's managed preview/runtime state."""
    return _call("project.preview_status", project)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
