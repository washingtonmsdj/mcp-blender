"""Canonical MCP entrypoint for ORDAX Studio.

The repository may still be installed or referenced as ``mcp-blender`` for
compatibility, but the MCP product exposed to clients is ORDAX Studio.
"""
from ordax_dev_agent.mcp_server import main, mcp, registry

__all__ = ["main", "mcp", "registry"]


if __name__ == "__main__":
    main()
