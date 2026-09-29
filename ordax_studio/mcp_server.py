"""Canonical MCP entrypoint for ORDAX Studio.

The repository may still be installed or referenced as ``mcp-blender`` for
compatibility, but the MCP product exposed to clients is ORDAX Studio.
"""
from ordax_dev_agent.mcp_server import main, mcp, registry

from .blender_connection import prepare_blender_connection as _prepare_blender_connection

__all__ = ["main", "mcp", "registry", "prepare_blender_connection"]


@mcp.tool()
def prepare_blender_connection(
    project: str | None = None,
    wait_seconds: float = 4.0,
) -> dict:
    """Resolve Blender connection/adoption state without opening a duplicate window."""
    agent = registry()
    selected = agent.select_available_project(project)
    return _prepare_blender_connection(
        agent,
        selected,
        wait_seconds=wait_seconds,
    )


if __name__ == "__main__":
    main()
